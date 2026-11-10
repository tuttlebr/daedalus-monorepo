#!/usr/bin/env python3
"""Exercise built agent -> gateway -> synthetic judge/provider, without live traffic.

Run with Python 3.11+, --agent-binary, --gateway-binary and --routes. Both binaries
must run on the same host. Supports Chat and native Responses provider routes with
loopback endpoints. No credentials, private prompts, Redis, or Kubernetes access
are required.
"""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import threading
import time
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PLAN = '{"type":"clarify","message":"Which lights?"}'
# The gateway's own upstream retry default when a client sets no max_retries.
GATEWAY_RETRIES = 2
AGENT_RETRIES = 1


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def ready(url, process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Fixture process exited before readiness")
        try:
            with urlopen(url + "/health", timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("Fixture readiness timed out")


def sse(events, named=False):
    return "".join(
        (f'event: {event["type"]}\n' if named else "") + f"data: {json.dumps(event)}\n\n"
        for event in events
    )


def chat_reply(body, malformed):
    """Return (content type, body, first stream event) for a Chat provider."""
    has_result = any(m["role"] == "tool" for m in body["messages"])
    wants_json = (body.get("response_format") or {}).get("type") == "json_object"
    message = {"role": "assistant", "content": PLAN if wants_json else "BOUNDARY_OK"}
    finish = "stop"
    if body.get("tools") and not has_result:
        message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "index": 0,
                    "id": "call_clock",
                    "type": "function",
                    "function": {
                        "name": "current_datetime_tool",
                        "arguments": "{invalid" if malformed else "{}",
                    },
                }
            ],
        }
        finish = "tool_calls"
    usage = {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11}
    envelope = {"id": "chatcmpl-boundary", "created": 1, "model": body["model"]}
    if not body.get("stream"):
        for call in message.get("tool_calls", []):
            del call["index"]
        reply = {
            **envelope,
            "object": "chat.completion",
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": usage,
        }
        return "application/json", json.dumps(reply), None
    envelope["object"] = "chat.completion.chunk"
    opening = {
        **envelope,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    events = [
        {**envelope, "choices": [{"index": 0, "delta": message, "finish_reason": None}]},
        {
            **envelope,
            "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
            "usage": usage,
        },
    ]
    return "text/event-stream", sse(events) + "data: [DONE]\n\n", sse([opening])


def responses_reply(body, malformed):
    """Return (content type, body, first stream event) for a Responses provider."""
    items = body["input"] if isinstance(body.get("input"), list) else []
    has_result = any(item.get("type") == "function_call_output" for item in items)
    text_format = (body.get("text") or {}).get("format") or {}
    text = PLAN if text_format.get("type") == "json_object" else "BOUNDARY_OK"
    use_tool = bool(body.get("tools")) and not has_result
    if use_tool:
        arguments = "{invalid" if malformed else "{}"
        item = {
            "id": "fc_boundary",
            "type": "function_call",
            "status": "completed",
            "call_id": "call_clock",
            "name": "current_datetime_tool",
            "arguments": arguments,
        }
    else:
        item = {
            "id": "msg_boundary",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }
    response = {
        "id": "resp_boundary",
        "object": "response",
        "created_at": 1,
        "status": "completed",
        "model": body["model"],
        "output": [item],
        "usage": {"input_tokens": 10, "output_tokens": 1, "total_tokens": 11},
    }
    if not body.get("stream"):
        return "application/json", json.dumps(response), None
    created = {
        "type": "response.created",
        "response": {**response, "status": "in_progress", "output": []},
    }
    del created["response"]["usage"]
    events = [created]
    if use_tool:
        position = {"item_id": "fc_boundary", "output_index": 0}
        events += [
            {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {**item, "status": "in_progress", "arguments": ""},
            },
            {"type": "response.function_call_arguments.delta", **position, "delta": arguments},
            {
                "type": "response.function_call_arguments.done",
                **position,
                "arguments": arguments,
            },
        ]
    else:
        position = {"item_id": "msg_boundary", "output_index": 0, "content_index": 0}
        part = {"type": "output_text", "text": "", "annotations": []}
        events += [
            {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {**item, "status": "in_progress", "content": []},
            },
            {"type": "response.content_part.added", **position, "part": part},
            {"type": "response.output_text.delta", **position, "delta": text},
            {"type": "response.output_text.done", **position, "text": text},
            {"type": "response.content_part.done", **position, "part": {**part, "text": text}},
        ]
    events += [
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {"type": "response.completed", "response": response},
    ]
    for sequence, event in enumerate(events):
        event["sequence_number"] = sequence
    return "text/event-stream", sse(events, named=True), sse(events[:1], named=True)


def effort(payload):
    """Provider-native reasoning effort of a Chat or Responses payload/default."""
    if "reasoning_effort" in payload:
        return payload["reasoning_effort"]
    return payload["reasoning"]["effort"]


def tool_results(payload):
    """Call IDs of tool results in a Chat or Responses provider request."""
    if "messages" in payload:
        return [m["tool_call_id"] for m in payload["messages"] if m["role"] == "tool"]
    return [
        item["call_id"]
        for item in payload["input"]
        if isinstance(item, dict) and item.get("type") == "function_call_output"
    ]


def check(agent_binary, gateway_binary, routes_path):
    source = Path(routes_path).read_text()
    config = tomllib.loads(source)
    replies = {"openai_chat": chat_reply, "openai_responses": responses_reply}
    if any(c["format"] not in replies for c in config["llm_clients"].values()):
        raise ValueError("Synthetic peer supports Chat and Responses provider routes")
    state = {"providers": [], "judges": 0, "mode": "normal"}

    class Peer(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/v1/systemone":
                state["judges"] += 1
                if state["mode"] == "timeout":
                    time.sleep(0.2)
                probabilities = {
                    name: 0.0
                    for name in (
                        *config["routes"]["stage"]["classifier"]["choices"],
                        "uncertain",
                    )
                }
                choice = state.get("choice", "low")
                probabilities[choice] = 1.0
                data = json.dumps(
                    {
                        "model": "fixture-judge",
                        "answers": {
                            "effort": {
                                "type": "choice",
                                "choice": choice,
                                "confidence": 1.0,
                                "probabilities": probabilities,
                            }
                        },
                        "usage": {"input_tokens": 10, "output_tokens": 0},
                    }
                )
                content_type = "application/json"
            elif self.path in ("/v1/chat/completions", "/v1/responses"):
                state["providers"].append(body)
                state["call_ids"].append(self.headers.get("x-request-id"))
                if state["mode"] == "persistent_failure":
                    self.send_error(503)
                    return
                if state["mode"] == "upstream_failure":
                    state["mode"] = "normal"
                    self.send_error(503)
                    return
                reply = chat_reply if self.path.endswith("completions") else responses_reply
                content_type, data, opening = reply(body, state["mode"] == "malformed")
                if state["mode"] == "malformed":
                    state["mode"] = "normal"
                if state["mode"] == "midstream_abort":
                    # One complete event, then drop the connection without the
                    # terminating chunk: an upstream transport failure in-stream.
                    state["mode"] = "normal"
                    opening = opening.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Transfer-Encoding", "chunked")
                    self.end_headers()
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(opening), opening))
                    self.wfile.flush()
                    time.sleep(0.05)
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.close_connection = True
                    return
            else:
                self.send_error(404)
                return
            data = data.encode()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    peer = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
    thread = threading.Thread(target=peer.serve_forever, daemon=True)
    thread.start()
    processes = []
    try:
        with tempfile.TemporaryDirectory(
            prefix="daedalus-effort-boundary-"
        ) as directory:
            directory = Path(directory)
            base = f"http://127.0.0.1:{peer.server_port}/v1"
            for client in config["llm_clients"].values():
                source = source.replace(client["base_url"], base)
            source = source.replace(
                config["routes"]["stage"]["classifier"]["base_url"], base
            )
            source = re.sub(r"(?m)^extra_headers = .*\n", "", source)
            source = source.replace('model = "auto"', 'model = "fixture-judge"')
            source = source.replace(
                'max_input_tokens = "auto"', "max_input_tokens = 16384"
            )
            source = source.replace("truncate_input = true", "truncate_input = false")
            source = source.replace("timeout_ms = 2000", "timeout_ms = 100")
            routes = directory / "routes.toml"
            routes.write_text(source)
            gateway_port, agent_port = port(), port()
            gateway_url, agent_url = (
                f"http://127.0.0.1:{gateway_port}",
                f"http://127.0.0.1:{agent_port}",
            )
            # Canonical explicit levels match the current gateway inventory.
            model_routes = {level: "daedalus/" + level for level in config["targets"]}
            agent_config = {
                "functions": {"current_datetime_tool": {"_type": "current_datetime"}},
                "llms": {
                    "main": {
                        "base_url": gateway_url + "/v1",
                        "model_name": "daedalus",
                        "api_type": "responses",
                        "api_key": "synthetic",
                        "max_retries": AGENT_RETRIES,
                    }
                },
                "workflow": {
                    "_type": "daedalus_rust_agent",
                    "llm_name": "main",
                    "tools": ["current_datetime_tool"],
                    "model_routes": model_routes,
                },
            }
            path = directory / "agent.json"
            path.write_text(json.dumps(agent_config))
            env = {
                "PATH": os.environ.get("PATH", ""),
                "DAEDALUS_CONFIG_FILE": str(path),
                "DAEDALUS_PORT": str(agent_port),
                "DAEDALUS_INTERNAL_API_TOKEN": "fixture-internal",
                "DAEDALUS_MEMORY_MODE": "disabled",
                "DAEDALUS_PREPARATION": "rust",
                "DAEDALUS_AUTHORIZATION": "rust",
                "DAEDALUS_TOOL_EXECUTOR": "disabled",
            }
            for client in config["llm_clients"].values():
                if client.get("api_key_env"):
                    env[client["api_key_env"]] = "synthetic"
            internal = {
                "Content-Type": "application/json",
                "x-daedalus-internal-token": "fixture-internal",
                "x-user-id": "synthetic-user",
            }
            with (directory / "process.log").open("w+") as log:

                def logged(*needles):
                    log.flush()
                    return [
                        line
                        for line in (directory / "process.log").read_text().splitlines()
                        if all(needle in line for needle in needles)
                    ]

                try:
                    for command, url in [
                        (
                            [
                                gateway_binary,
                                "--config",
                                str(routes),
                                "--host",
                                "127.0.0.1",
                                "--port",
                                str(gateway_port),
                            ],
                            gateway_url,
                        ),
                        ([agent_binary], agent_url),
                    ]:
                        process = subprocess.Popen(
                            command, env=env, stdout=log, stderr=subprocess.STDOUT
                        )
                        processes.append(process)
                        ready(url, process)

                    cases = [
                        (None, "normal"),
                        *[(None, "classify_" + level) for level in ("instant", "high", "max")],
                        *[(level, "normal") for level in model_routes],
                        (None, "timeout"),
                        ("low", "upstream_failure"),
                        ("low", "midstream_abort"),
                        ("low", "persistent_failure"),
                        (None, "persistent_failure"),
                        ("low", "malformed"),
                        *[
                            (retired, "rejected")
                            for retired in (
                                "default",
                                "deep",
                                "deep_max",
                                "none",
                                *(
                                    level
                                    for level in ("medium", "xhigh")
                                    if level not in model_routes
                                ),
                            )
                        ],
                    ]
                    for index, (profile, mode) in enumerate(cases):
                        choice = mode.removeprefix("classify_") if mode.startswith("classify_") else "low"
                        state.update(providers=[], call_ids=[], judges=0, mode=mode, choice=choice)
                        body = {
                            "stream": True,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Read the clock once, then reply BOUNDARY_OK.",
                                }
                            ],
                        }
                        if profile is not None:
                            body["additional_props"] = {"model_profile": profile}
                        request = Request(
                            agent_url + "/v1/chat/completions",
                            data=json.dumps(body).encode(),
                            headers={**internal, "x-daedalus-request-id": f"fixture-{index}"},
                        )
                        try:
                            with urlopen(request, timeout=15) as response:
                                text = response.read().decode()
                        except HTTPError as error:
                            text = error.read().decode()
                        if mode == "rejected":
                            assert not state["providers"] and state["judges"] == 0, (
                                profile,
                                state,
                            )
                            assert '"finish_reason":"error"' in text, text
                            assert "Function Start:" not in text, text
                        elif mode == "persistent_failure":
                            # Retries multiply: each agent attempt is retried by
                            # the gateway, and the automatic route then tries
                            # its fallback target. Pin the combined bound.
                            assert '"finish_reason":"error"' in text, text
                            assert "Function Start:" not in text, text
                            stage = config["routes"]["stage"]
                            targets = [profile or stage["classifier"]["choices"][choice]["target"]]
                            if profile is None and stage["default_target"] not in targets:
                                targets.append(stage["default_target"])
                            per_attempt = sum(
                                1
                                + config["llm_clients"][config["targets"][target]["llm_client"]].get(
                                    "max_retries", GATEWAY_RETRIES
                                )
                                for target in targets
                            )
                            assert len(state["providers"]) == (1 + AGENT_RETRIES) * per_attempt, (
                                profile,
                                len(state["providers"]),
                                per_attempt,
                            )
                            assert state["judges"] == (
                                1 + AGENT_RETRIES if profile is None else 0
                            ), state["judges"]
                        elif mode == "malformed":
                            # A completed provider reply with invalid tool JSON is
                            # rejected before execution; it is not a transport retry.
                            assert '"finish_reason":"error"' in text, text
                            assert "Function Start:" not in text, text
                            assert len(state["providers"]) == 1 and state["judges"] == 0
                        else:
                            assert (
                                "BOUNDARY_OK" in text
                                and '"finish_reason":"stop"' in text
                            ), (profile, mode, text)
                            assert (
                                text.count("Function Start: current_datetime_tool") == 1
                            ), text
                            failed = mode in ("upstream_failure", "midstream_abort")
                            assert len(state["providers"]) == (3 if failed else 2), (
                                profile,
                                mode,
                                state,
                            )
                            target = (
                                config["routes"]["stage"]["default_target"]
                                if mode == "timeout"
                                else profile or config["routes"]["stage"]["classifier"]["choices"][choice]["target"]
                            )
                            for payload in state["providers"]:
                                assert (
                                    payload["model"]
                                    == config["targets"][target]["model"]
                                )
                                assert effort(payload) == effort(
                                    config["targets"][target]["extra_body"]
                                )
                            assert state["judges"] == (2 if profile is None else 0), (
                                state
                            )
                            assert tool_results(state["providers"][-1]) == ["call_clock"], (
                                state["providers"][-1]
                            )
                        if mode == "midstream_abort":
                            # The gateway reports the lost upstream connection as
                            # an in-stream error; the agent retries only its
                            # transport envelope, as a new logical call.
                            assert len(
                                logged(
                                    "model_retry_scheduled",
                                    f"fixture-{index}",
                                    '"error_kind":"upstream_transport"',
                                )
                            ) == 1, logged("model_retry_scheduled", f"fixture-{index}")
                        expected_ids = []
                        run_id = f"fixture-{index}".encode()
                        # The gateway retries a failed upstream request under
                        # the caller's ID; only an agent attempt gets a new one.
                        logical_calls = len(state["providers"]) - (
                            1 if mode == "upstream_failure" else 0
                        )
                        repeats = 1
                        if mode == "persistent_failure":
                            logical_calls = 1 + AGENT_RETRIES
                            repeats = len(state["providers"]) // logical_calls
                        for attempt in range(1, logical_calls + 1):
                            expected_ids.append(
                                "dc-"
                                + hashlib.sha256(
                                    b"daedalus-model-call-v1"
                                    + len(run_id).to_bytes(8, "big")
                                    + run_id
                                    + attempt.to_bytes(8, "big")
                                ).hexdigest()
                            )
                        wire_ids = (
                            expected_ids[:1] + expected_ids
                            if mode == "upstream_failure"
                            else [call_id for call_id in expected_ids for _ in range(repeats)]
                        )
                        assert state["call_ids"] == wire_ids, state["call_ids"]
                        for call_id in expected_ids:
                            # The same ID occurs in backend model_call_started and gateway spans.
                            assert len(logged(call_id, "model_call_started")) == 1
                            assert logged(call_id, "libsy.run"), call_id
                        print(
                            json.dumps(
                                {
                                    "profile": profile,
                                    "mode": mode,
                                    "provider_calls": len(state["providers"]),
                                    "classifier_calls": state["judges"],
                                    "passed": True,
                                }
                            ),
                            flush=True,
                        )

                    # A stateless, non-streaming Chat forward on the automatic
                    # route: the caller's stream choice, JSON mode and an opaque
                    # correlation ID must survive whichever transport the
                    # selected provider uses.
                    state.update(providers=[], call_ids=[], judges=0, mode="normal", choice="low")
                    request = Request(
                        agent_url + "/internal/autonomy/plan",
                        data=json.dumps(
                            {
                                "instructions": "Use the game scene at kickoff.",
                                "context": {"settings": {}},
                            }
                        ).encode(),
                        headers=internal,
                    )
                    try:
                        with urlopen(request, timeout=15) as response:
                            content_type = response.headers.get("Content-Type", "")
                            text = response.read().decode()
                    except HTTPError as error:
                        raise AssertionError(
                            ("autonomy_plan", error.code, error.read().decode(), state)
                        ) from error
                    assert content_type.startswith("application/json"), content_type
                    reply = json.loads(text)["choices"][0]
                    assert reply["finish_reason"] == "stop", reply
                    assert json.loads(reply["message"]["content"]) == json.loads(PLAN)
                    assert len(state["providers"]) == 1 and state["judges"] == 1, state
                    payload = state["providers"][0]
                    assert not payload.get("stream"), payload
                    target = config["routes"]["stage"]["classifier"]["choices"]["low"]["target"]
                    assert payload["model"] == config["targets"][target]["model"]
                    assert (
                        payload.get("response_format")
                        or (payload.get("text") or {}).get("format")
                    ) == {"type": "json_object"}, payload
                    (call_id,) = state["call_ids"]
                    assert re.fullmatch(r"dc-[0-9a-f]{64}", call_id or ""), call_id
                    assert len(
                        logged(call_id, "model_forward_started", '"origin":"autonomy_plan"')
                    ) == 1
                    assert logged(call_id, "libsy.run"), call_id
                    print(
                        json.dumps(
                            {
                                "profile": None,
                                "mode": "autonomy_plan",
                                "provider_calls": 1,
                                "classifier_calls": 1,
                                "passed": True,
                            }
                        ),
                        flush=True,
                    )
                except Exception:
                    log.flush()
                    log.seek(0)
                    print(log.read()[-12000:])  # Synthetic fixture logs only.
                    raise
                finally:
                    for process in reversed(processes):
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
    finally:
        peer.shutdown()
        peer.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-binary", required=True)
    parser.add_argument("--gateway-binary", required=True)
    parser.add_argument("--routes", type=Path, required=True)
    args = parser.parse_args()
    check(
        str(Path(args.agent_binary).resolve()),
        str(Path(args.gateway_binary).resolve()),
        args.routes,
    )
