#!/usr/bin/env python3
"""Built agent runtime -> synthetic MCP server with fixed latency, scripted model.

Checks how the runtime schedules MCP calls that one model response proposes
for the same server: which calls may overlap, that other operations stay
exclusive and ordered, that results stay bound to their call IDs, and that one
call's error or timeout leaves its siblings intact. Timings are reported for a
paired baseline/candidate comparison and are never asserted.

Run it inside the agent image under test (standard library only, loopback
only), once per arm, alternating the order between repetitions:

    docker run --rm --network none \
        -v <this scripts directory>:/check:ro -v <private output dir>:/out \
        --entrypoint python3 <agent-image> /check/check_mcp_read_overlap.py \
        --report /out/<arm>-<repetition>.json

`--bound N` (1 to 8, default 4) sets the overlap bound of the opted-in fixture
groups; the capacity scenario then proposes N + 2 reads.

No real model, MCP service, credential or cluster is used. A scripted model
establishes scheduling and result delivery, not real-model behaviour.
"""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY = 0.4
HANG = 5.0
GROUP_TIMEOUT = 2
BOUND = 4
RUNTIME = "/workspace/daedalus-runtime"

# group -> (tools exposed, read_only tools, opt-in bound or None, deferred)
GROUPS = {
    "fx_reads": (["read_item", "write_item"], ["read_item"], BOUND, False),
    "fx_plain": (["read_item"], ["read_item"], None, False),
    "fx_auto": (["lookup_item"], [], BOUND, False),
    "fx_deferred": (["read_item"], ["read_item"], 3, True),
}


def read(group, item):
    return (f"{group}__read_item", {"id": item})


# scenario -> rounds; each round is the batch one model response proposes.
SCENARIOS = {
    "READS4": [[read("fx_reads", i) for i in "abcd"]],
    "MIXED": [
        [
            read("fx_reads", "a"),
            ("fx_reads__write_item", {"id": "w"}),
            read("fx_reads", "b"),
            read("fx_reads", "c"),
        ]
    ],
    "ERRORS": [
        [
            read("fx_reads", "a"),
            read("fx_reads", "err1"),
            read("fx_reads", "rpc1"),
            read("fx_reads", "b"),
        ],
        [read("fx_reads", "c")],
    ],
    "TIMEOUT": [
        [read("fx_reads", "a"), read("fx_reads", "hang1"), read("fx_reads", "b")],
        [read("fx_reads", "c")],
    ],
    "DEFAULT_SERIAL": [[read("fx_plain", i) for i in "abcd"]],
    "AUTO_ONLY": [[("fx_auto__lookup_item", {"id": i}) for i in "abcd"]],
    "CROSS_GROUP": [
        [
            read("fx_reads", "a"),
            read("fx_plain", "b"),
            read("fx_reads", "c"),
            read("fx_plain", "d"),
        ]
    ],
    "CAP": [[read("fx_reads", i) for i in "abcdef"]],
    "DEFERRED": [
        [("fx_deferred__connect", {})],
        [read("fx_deferred", i) for i in "abc"],
    ],
    "TWO_A": [[read("fx_reads", i) for i in "abcd"]],
    "TWO_B": [[read("fx_reads", i) for i in "efgh"]],
}


def configure(bound):
    """Use another overlap bound for the opted-in groups and the capacity case."""
    global BOUND
    BOUND = bound
    for name in ("fx_reads", "fx_auto"):
        tools, read_only, _, deferred = GROUPS[name]
        GROUPS[name] = (tools, read_only, bound, deferred)
    SCENARIOS["CAP"] = [[read("fx_reads", i) for i in "abcdefghij"[: bound + 2]]]


def value(item):
    return hashlib.sha256(("fixture:" + item).encode()).hexdigest()[:16]


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.in_flight = {}
        self.calls = []  # dicts with group, tool, id, run, start, end, concurrent
        self.sessions = {}
        self.model = {}  # run marker -> list of events
        self.failures = []

    def run_events(self, marker):
        with self.lock:
            return self.model.setdefault(marker, [])


STATE = State()
T0 = time.monotonic()


def now():
    return round((time.monotonic() - T0) * 1000, 1)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def reply(self, body, status=200, headers=()):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for key, text in headers:
            self.send_header(key, text)
        self.end_headers()
        self.wfile.write(data)

    def empty(self, status):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        # No standalone server stream is offered.
        self.empty(405)

    def do_DELETE(self):
        self.empty(200)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        try:
            if self.path.startswith("/mcp/"):
                self.mcp(self.path.split("/")[2], body)
            elif self.path == "/v1/chat/completions":
                self.model(body)
            else:
                self.reply({"error": "unexpected endpoint"}, 404)
        except BrokenPipeError:
            pass
        except Exception as exc:  # fixture defect or contract violation
            STATE.failures.append(f"{self.path}: {exc!r}")
            self.close_connection = True

    # ---- MCP server ----
    def mcp(self, group, body):
        tools, _, _, _ = GROUPS[group]
        method = body.get("method")
        if "id" not in body:
            self.empty(202)
            return
        session = self.headers.get("mcp-session-id")
        if method == "initialize":
            session = uuid.uuid4().hex
            with STATE.lock:
                STATE.sessions[session] = group
            self.reply(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "protocolVersion": body["params"]["protocolVersion"],
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fixture", "version": "1"},
                    },
                },
                headers=[("mcp-session-id", session)],
            )
            return
        if method == "tools/list":
            self.reply(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "tools": [
                            {
                                "name": name,
                                "description": f"Fixture operation {name}.",
                                "annotations": {
                                    "readOnlyHint": name != "write_item",
                                    "destructiveHint": name == "write_item",
                                },
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"id": {"type": "string"}},
                                    "required": ["id"],
                                    "additionalProperties": False,
                                },
                            }
                            for name in tools
                        ]
                    },
                }
            )
            return
        if method != "tools/call":
            self.reply(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "error": {"code": -32601, "message": "Unknown method"},
                }
            )
            return
        name = body["params"]["name"]
        item = body["params"].get("arguments", {}).get("id", "")
        with STATE.lock:
            STATE.in_flight[group] = STATE.in_flight.get(group, 0) + 1
            record = {
                "group": group,
                "tool": name,
                "id": item,
                "session": session,
                "start": now(),
                "end": None,
                "concurrent_at_start": STATE.in_flight[group],
            }
            STATE.calls.append(record)
        try:
            time.sleep(HANG if item.startswith("hang") else DELAY)
        finally:
            with STATE.lock:
                STATE.in_flight[group] -= 1
                record["end"] = now()
        if item.startswith("rpc"):
            self.reply(
                {
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "error": {"code": -32603, "message": "fixture rpc failure"},
                }
            )
            return
        failed = item.startswith("err")
        text = json.dumps(
            {"error": "fixture tool failure", "id": item}
            if failed
            else {"operation": name, "id": item, "value": value(item)}
        )
        self.reply(
            {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "content": [{"type": "text", "text": text}],
                    "isError": failed,
                },
            }
        )

    # ---- scripted model ----
    def model(self, body):
        received = now()
        user = next(m["content"] for m in body["messages"] if m["role"] == "user")
        scenario, marker = user.split()[:2]
        rounds = SCENARIOS[scenario]
        events = STATE.run_events(marker)
        results = {
            m["tool_call_id"]: m["content"]
            for m in body["messages"]
            if m["role"] == "tool"
        }
        done = 0
        for index, batch in enumerate(rounds):
            if all(f"c{index}_{i}" in results for i in range(len(batch))):
                done = index + 1
            else:
                break
        events.append(
            {
                "kind": "request",
                "at": received,
                "round": done,
                "results": {
                    key: {
                        "sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "bytes": len(text.encode()),
                    }
                    for key, text in sorted(results.items())
                },
                "advertised": sorted(
                    tool["function"]["name"] for tool in body.get("tools", [])
                ),
            }
        )
        problems = []
        for index, batch in enumerate(rounds[:done]):
            for i, (name, arguments) in enumerate(batch):
                text = results[f"c{index}_{i}"]
                item = arguments.get("id", "")
                if name.endswith("__connect"):
                    ok = "Connected" in text
                elif item.startswith("hang"):
                    ok = "did not return a confirmed result" in text
                elif item.startswith("rpc"):
                    ok = "mcp_rpc_error" in text and "fixture rpc failure" in text
                elif item.startswith("err"):
                    ok = "fixture tool failure" in text and item in text
                else:
                    ok = value(item) in text and "fixture tool failure" not in text
                if not ok:
                    problems.append(f"c{index}_{i}:{name}:{item}")
                    STATE.failures.append(
                        f"unexpected result for {scenario} c{index}_{i} ({item}): {text[:400]!r}"
                    )
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()

        def chunk(delta, reason=None):
            payload = {
                "id": "fixture",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": delta, "finish_reason": reason}],
            }
            self.wfile.write(("data: " + json.dumps(payload) + "\n\n").encode())

        if problems:
            chunk({"role": "assistant", "content": f"{scenario} FAILED {problems}"})
            chunk({}, "stop")
        elif done < len(rounds):
            chunk({"role": "assistant"})
            for i, (name, arguments) in enumerate(rounds[done]):
                chunk(
                    {
                        "tool_calls": [
                            {
                                "index": i,
                                "id": f"c{done}_{i}",
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": json.dumps(arguments),
                                },
                            }
                        ]
                    }
                )
            chunk({}, "tool_calls")
        else:
            chunk({"role": "assistant", "content": f"{scenario} verified {marker}"})
            chunk({}, "stop")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        events.append({"kind": "response", "at": now(), "round": done})
        self.close_connection = True


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def config(peer_port):
    groups = {}
    for name, (tools, read_only, bound, deferred) in GROUPS.items():
        group = {
            "_type": "mcp_client",
            "server": {"url": f"http://127.0.0.1:{peer_port}/mcp/{name}"},
            "include": tools,
            "approval_policy": "auto_approve",
            "tool_call_timeout": GROUP_TIMEOUT,
            "tool_overrides": {
                tool: {"approval_policy": "read_only"} for tool in read_only
            },
        }
        if bound is not None:
            group["max_concurrency"] = bound
        if deferred:
            group["defer_discovery"] = True
            group["discovery_description"] = "Fixture deferred reads."
        groups[name] = group
    return {
        "llms": {
            "main": {
                "model_name": "fixture",
                "api_type": "chat",
                "api_key": "fixture",
                "base_url": f"http://127.0.0.1:{peer_port}/v1",
            }
        },
        "workflow": {
            "_type": "daedalus_rust_agent",
            "llm_name": "main",
            "tools": list(GROUPS),
            "max_iterations": 8,
            "parallel_tool_calls": True,
            "instructions": "Use the proposed tools and report the result.",
        },
        "function_groups": groups,
    }


def chat(agent_port, token, scenario, user="fixture"):
    marker = uuid.uuid4().hex[:12]
    request = urllib.request.Request(
        f"http://127.0.0.1:{agent_port}/v1/chat/completions",
        data=json.dumps(
            {
                "stream": True,
                "messages": [{"role": "user", "content": f"{scenario} {marker}"}],
            }
        ).encode(),
        headers={
            "content-type": "application/json",
            "x-daedalus-internal-token": token,
            "x-user-id": user,
        },
    )
    started = now()
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8", "replace")
    return marker, started, now(), text


def summarize(scenario, marker, started, finished, text, since):
    events = STATE.run_events(marker)
    with STATE.lock:
        calls = [dict(c) for c in STATE.calls[since:]]
    phases = []
    for index in range(len(events) - 1):
        if events[index]["kind"] == "response" and events[index + 1]["kind"] == "request":
            phases.append(round(events[index + 1]["at"] - events[index]["at"], 1))
    requests = [e for e in events if e["kind"] == "request"]
    peak = {}
    for group in GROUPS:
        marks = sorted(
            [(c["start"], 1) for c in calls if c["group"] == group]
            + [(c["end"], -1) for c in calls if c["group"] == group and c["end"]],
            key=lambda mark: (mark[0], mark[1]),
        )
        level = best = 0
        for _, step in marks:
            level += step
            best = max(best, level)
        if best:
            peak[group] = best
    return {
        "scenario": scenario,
        "answer_verified": f"{scenario} verified {marker}" in text,
        "latency_ms": round(finished - started, 1),
        "tool_phase_ms": phases,
        "model_requests": len(requests),
        "mcp_calls": len(calls),
        "peak_in_flight": peak,
        "sessions": len({c["session"] for c in calls}),
        "results": requests[-1]["results"] if requests else {},
        "calls": [
            {k: c[k] for k in ("group", "tool", "id", "start", "end")} for c in calls
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--runtime", default=RUNTIME)
    parser.add_argument("--bound", type=int, choices=range(1, 9), default=BOUND)
    args = parser.parse_args()
    if args.bound != BOUND:
        configure(args.bound)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    agent_port, token = free_port(), uuid.uuid4().hex
    directory = tempfile.mkdtemp(prefix="mcp-overlap-")
    path = os.path.join(directory, "config.yaml")
    with open(path, "w") as handle:
        json.dump(config(server.server_port), handle)  # JSON is valid YAML
    log = open(os.path.join(directory, "agent.log"), "w")
    process = subprocess.Popen(
        [args.runtime],
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": directory,
            "DAEDALUS_CONFIG_FILE": path,
            "DAEDALUS_INTERNAL_API_TOKEN": token,
            "DAEDALUS_HOST": "127.0.0.1",
            "DAEDALUS_PORT": str(agent_port),
            "DAEDALUS_PREPARATION": "rust",
            "DAEDALUS_AUTHORIZATION": "rust",
            "DAEDALUS_TOOL_EXECUTOR": "disabled",
            "DAEDALUS_MEMORY_MODE": "disabled",
            "REDIS_URL": "redis://127.0.0.1:1",
        },
        stdout=log,
        stderr=log,
    )
    report = {"runtime": args.runtime, "delay_ms": DELAY * 1000, "bound": BOUND}
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError("agent runtime exited during startup")
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{agent_port}/health", timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("agent runtime not ready")
        scenarios = {}
        for scenario in (
            "READS4",
            "MIXED",
            "ERRORS",
            "TIMEOUT",
            "DEFAULT_SERIAL",
            "AUTO_ONLY",
            "CROSS_GROUP",
            "CAP",
            "DEFERRED",
        ):
            since = len(STATE.calls)
            marker, started, finished, text = chat(agent_port, token, scenario)
            scenarios[scenario] = summarize(
                scenario, marker, started, finished, text, since
            )
            time.sleep(HANG if scenario == "TIMEOUT" else 0.05)
        # Two concurrent runs for one user share that user's sessions.
        since = len(STATE.calls)
        outcomes = {}

        def run(name):
            outcomes[name] = chat(agent_port, token, name)

        threads = [threading.Thread(target=run, args=(n,)) for n in ("TWO_A", "TWO_B")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        both = [
            summarize(name, *outcomes[name], since) for name in ("TWO_A", "TWO_B")
        ]
        scenarios["TWO_RUNS"] = {
            "scenario": "TWO_RUNS",
            "answer_verified": all(s["answer_verified"] for s in both),
            "latency_ms": max(s["latency_ms"] for s in both),
            "tool_phase_ms": [max(s["tool_phase_ms"][0] for s in both)],
            "model_requests": sum(s["model_requests"] for s in both),
            "mcp_calls": both[0]["mcp_calls"],
            "peak_in_flight": both[0]["peak_in_flight"],
            "sessions": both[0]["sessions"],
            "results": {
                f"{s['scenario']}:{key}": digest
                for s in both
                for key, digest in s["results"].items()
            },
            "calls": both[0]["calls"],
        }

        def spans(name, group, tool=None, item=None):
            return [
                (c["start"], c["end"])
                for c in scenarios[name]["calls"]
                if c["group"] == group
                and (tool is None or c["tool"] == tool)
                and (item is None or c["id"] == item)
            ]

        mixed = scenarios["MIXED"]["calls"]
        write = next(c for c in mixed if c["tool"] == "write_item")
        others = [c for c in mixed if c is not write]
        first = next(c for c in mixed if c["id"] == "a")
        later = [c for c in mixed if c["id"] in ("b", "c")]
        expected_calls = {
            name: sum(
                1 for batch in SCENARIOS[name] for call in batch
                if not call[0].endswith("__connect")
            )
            for name in SCENARIOS
        }
        checks = {
            "all_answers_verified": all(s["answer_verified"] for s in scenarios.values()),
            "no_fixture_failures": not STATE.failures,
            "call_counts": all(
                scenarios[name]["mcp_calls"] == expected_calls[name]
                for name in scenarios
                if name != "TWO_RUNS"
            )
            and scenarios["TWO_RUNS"]["mcp_calls"] == 8,
            "model_rounds": all(
                scenarios[name]["model_requests"] == len(SCENARIOS[name]) + 1
                for name in scenarios
                if name != "TWO_RUNS"
            )
            and scenarios["TWO_RUNS"]["model_requests"] == 4,
            "write_exclusive": all(
                o["end"] <= write["start"] or o["start"] >= write["end"] for o in others
            ),
            "write_ordered": first["end"] <= write["start"]
            and all(o["start"] >= write["end"] for o in later),
            "default_serial": scenarios["DEFAULT_SERIAL"]["peak_in_flight"] == {"fx_plain": 1},
            "auto_only_serial": scenarios["AUTO_ONLY"]["peak_in_flight"] == {"fx_auto": 1},
            "cross_group_plain_serial": scenarios["CROSS_GROUP"]["peak_in_flight"].get("fx_plain") == 1,
            "cap_within_bound": scenarios["CAP"]["peak_in_flight"]["fx_reads"] <= BOUND,
            "two_runs_within_bound": scenarios["TWO_RUNS"]["peak_in_flight"]["fx_reads"] <= BOUND,
            "deferred_within_bound": scenarios["DEFERRED"]["peak_in_flight"].get("fx_deferred", 0) <= 3,
            "timeout_recovers": len(spans("TIMEOUT", "fx_reads", item="c")) == 1,
        }
        report.update(
            {
                "passed": all(checks.values()),
                "checks": checks,
                "failures": STATE.failures,
                "scenarios": scenarios,
            }
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()
        with open(os.path.join(directory, "agent.log")) as handle:
            agent_log = handle.read()
        report["agent_log_lines"] = agent_log.count("\n")
        with open(args.report + ".agent.log", "w") as handle:
            handle.write(agent_log)
        with open(args.report, "w") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        server.shutdown()
    print(
        json.dumps(
            {
                "passed": report.get("passed"),
                "checks": report.get("checks"),
                "tool_phase_ms": {
                    name: s["tool_phase_ms"]
                    for name, s in report.get("scenarios", {}).items()
                },
                "peak_in_flight": {
                    name: s["peak_in_flight"]
                    for name, s in report.get("scenarios", {}).items()
                },
            },
            indent=1,
        )
    )
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
