#!/usr/bin/env python3
"""Exercise built agent -> gateway -> synthetic judge/provider, without live traffic.

Run with Python 3.11+, --agent-binary, --gateway-binary and --routes. Both binaries
must run on the same host. Supports Chat provider routes with loopback endpoints.
No credentials, private prompts, Redis, or Kubernetes access are required.
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


def check(agent_binary, gateway_binary, routes_path):
    source = Path(routes_path).read_text()
    config = tomllib.loads(source)
    if any(
        client["format"] != "openai_chat"
        for client in config["llm_clients"].values()
    ):
        raise ValueError("Synthetic peer supports only openai_chat provider routes")
    state = {"providers": [], "judges": 0, "mode": "normal"}

    class Peer(BaseHTTPRequestHandler):
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
                ).encode()
                content_type = "application/json"
            elif self.path == "/v1/chat/completions":
                state["providers"].append(body)
                state["call_ids"].append(self.headers.get("x-request-id"))
                if state["mode"] == "upstream_failure":
                    state["mode"] = "normal"
                    self.send_error(503)
                    return
                has_result = any(m["role"] == "tool" for m in body["messages"])
                delta = {"role": "assistant", "content": "BOUNDARY_OK"}
                finish = "stop"
                if not has_result:
                    delta = {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_clock",
                                "type": "function",
                                "function": {
                                    "name": "current_datetime_tool",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                    finish = "tool_calls"
                if state["mode"] == "malformed":
                    delta["tool_calls"][0]["function"]["arguments"] = "{invalid"
                    state["mode"] = "normal"
                envelope = {
                    "id": "chatcmpl-boundary",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": body["model"],
                }
                events = [
                    {
                        **envelope,
                        "choices": [
                            {"index": 0, "delta": delta, "finish_reason": None}
                        ],
                    },
                    {
                        **envelope,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 1,
                            "total_tokens": 11,
                        },
                    },
                ]
                data = (
                    "".join("data: " + json.dumps(event) + "\n\n" for event in events)
                    + "data: [DONE]\n\n"
                ).encode()
                content_type = "text/event-stream"
            else:
                self.send_error(404)
                return
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
                        "max_retries": 1,
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
            with (directory / "process.log").open("w+") as log:
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
                            headers={
                                "Content-Type": "application/json",
                                "x-daedalus-internal-token": "fixture-internal",
                                "x-user-id": "synthetic-user",
                                "x-daedalus-request-id": f"fixture-{index}",
                            },
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
                            expected_count = 3 if mode == "upstream_failure" else 2
                            assert len(state["providers"]) == expected_count, (
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
                                assert (
                                    payload["reasoning_effort"]
                                    == config["targets"][target]["extra_body"][
                                        "reasoning_effort"
                                    ]
                                )
                            assert state["judges"] == (2 if profile is None else 0), (
                                state
                            )
                            history = state["providers"][-1]["messages"]
                            assert sum(m["role"] == "tool" for m in history) == 1, (
                                history
                            )
                            assert (
                                next(m for m in history if m["role"] == "tool")[
                                    "tool_call_id"
                                ]
                                == "call_clock"
                            )
                        expected_ids = []
                        run_id = f"fixture-{index}".encode()
                        logical_calls = len(state["providers"]) - (
                            1 if mode == "upstream_failure" else 0
                        )
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
                            else expected_ids
                        )
                        assert state["call_ids"] == wire_ids, state["call_ids"]
                        log.flush()
                        observed_logs = (directory / "process.log").read_text()
                        for call_id in expected_ids:
                            # The same ID occurs in backend model_call_started and gateway spans.
                            assert (
                                len(
                                    [
                                        line
                                        for line in observed_logs.splitlines()
                                        if call_id in line
                                        and "model_call_started" in line
                                    ]
                                )
                                == 1
                            )
                            assert any(
                                call_id in line and "libsy.run" in line
                                for line in observed_logs.splitlines()
                            ), call_id
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
