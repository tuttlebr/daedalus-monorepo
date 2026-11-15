#!/usr/bin/env python3
"""Built agent -> built Kubernetes MCP -> isolated API/command fixtures.

No real kubeconfig, cluster, credentials, or model endpoint is used. Requires
httpx/PyYAML, a local agent image, and a locally built Kubernetes MCP binary.
"""

import argparse
import contextlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import uuid

import httpx
import yaml


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Fixture:
    def __init__(self):
        self.deletes = []
        self.reads = 0
        self.model_errors = []
        self.requests = []

    def handler(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, value, status=200):
                data = json.dumps(value).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/api":
                    self.reply(
                        {"kind": "APIVersions", "apiVersion": "v1", "versions": ["v1"]}
                    )
                elif path == "/apis":
                    version = {
                        "groupVersion": "metrics.k8s.io/v1beta1",
                        "version": "v1beta1",
                    }
                    self.reply(
                        {
                            "kind": "APIGroupList",
                            "apiVersion": "v1",
                            "groups": [
                                {
                                    "name": "metrics.k8s.io",
                                    "versions": [version],
                                    "preferredVersion": version,
                                }
                            ],
                        }
                    )
                elif path in ("/api/v1", "/apis/metrics.k8s.io/v1beta1"):
                    core = path == "/api/v1"
                    self.reply(
                        {
                            "kind": "APIResourceList",
                            "apiVersion": "v1",
                            "groupVersion": "v1" if core else "metrics.k8s.io/v1beta1",
                            "resources": [
                                {
                                    "name": "pods",
                                    "singularName": "pod" if core else "",
                                    "kind": "Pod" if core else "PodMetrics",
                                    "namespaced": True,
                                    "verbs": ["get", "list", "delete"]
                                    if core
                                    else ["get", "list"],
                                }
                            ],
                        }
                    )
                elif path == "/api/v1/namespaces/fixture/pods":
                    fixture.reads += 1
                    items = (
                        [
                            {
                                "apiVersion": "v1",
                                "kind": "Pod",
                                "metadata": {
                                    "name": "sample",
                                    "namespace": "fixture",
                                    "deletionTimestamp": "2026-01-01T00:00:00Z",
                                },
                            }
                        ]
                        if fixture.reads == 1
                        else []
                    )
                    self.reply({"apiVersion": "v1", "kind": "PodList", "items": items})
                else:
                    self.reply({"error": "unexpected fixture path"}, 404)

            def do_DELETE(self):
                fixture.deletes.append(self.path)
                if self.path == "/api/v1/namespaces/fixture/pods/sample":
                    self.reply(
                        {"kind": "Status", "apiVersion": "v1", "status": "Success"}
                    )
                elif self.path == "/api/v1/namespaces/fixture/pods/forbidden":
                    self.reply(
                        {
                            "kind": "Status",
                            "apiVersion": "v1",
                            "status": "Failure",
                            "reason": "Forbidden",
                            "code": 403,
                            "message": "fixture policy forbids deleting this pod",
                        },
                        403,
                    )
                else:
                    self.reply(
                        {
                            "kind": "Status",
                            "apiVersion": "v1",
                            "status": "Failure",
                            "reason": "MethodNotAllowed",
                            "code": 405,
                            "message": "wrong resource API",
                        },
                        405,
                    )

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fixture.requests.append(body)
                try:
                    self.model(body)
                except Exception as exc:
                    fixture.model_errors.append(repr(exc))
                    print("model fixture failure:", repr(exc), flush=True)
                    self.close_connection = True

            def model(self, body):
                assert self.path == "/v1/chat/completions"
                scenario = next(
                    m["content"] for m in body["messages"] if m["role"] == "user"
                )
                results = [
                    json.loads(m["content"])
                    for m in body["messages"]
                    if m["role"] == "tool"
                ]
                ordinary = {"kind": "pods", "namespace": "fixture"}
                sequences = {
                    "DELETE_STATES": [
                        ("deleteResource", {**ordinary, "name": "sample"}),
                        ("listResources", ordinary),
                        ("listResources", ordinary),
                    ],
                    "REJECTED": [("deleteResource", {**ordinary, "name": "forbidden"})],
                    "KUBECTL_FAILED": [
                        (
                            "runKubectlCommand",
                            {"command": "kubectl delete pod sample -n fixture"},
                        )
                    ],
                    "KUBECTL_TIMEOUT": [
                        (
                            "runKubectlCommand",
                            {"command": "kubectl timeout", "timeout": 1},
                        )
                    ],
                    "READ_ONLY": [("listResources", ordinary)],
                }
                sequence = sequences[scenario]
                if results:
                    result = results[-1]
                    if result.get("status") == "error":
                        result = json.loads(result["content"])
                    text = result["content"][0]["text"]
                    if scenario == "DELETE_STATES":
                        assert not result.get("isError", False)
                        if len(results) == 1:
                            assert (
                                "accepted" in text
                                and "deleted successfully" not in text
                            )
                        elif len(results) == 2:
                            assert "sample" in text, (
                                "acceptance must precede disappearance"
                            )
                        else:
                            assert "sample" not in text, (
                                "completion requires observed absence"
                            )
                    elif scenario == "REJECTED":
                        assert result["isError"] and "fixture policy forbids" in text
                        assert "unconfirmed" not in text
                    elif scenario.startswith("KUBECTL_"):
                        payload = json.loads(text)
                        assert result["isError"] and payload["exitCode"] != 0
                        if scenario == "KUBECTL_FAILED":
                            assert (
                                payload["exitCode"] == 7
                                and payload["stdout"] == "partial output\n"
                            )
                            assert "synthetic failure" in payload["stderr"]
                        else:
                            assert "timed out" in payload["error"]
                    else:
                        assert not result.get("isError", False)
                if len(results) < len(sequence):
                    name, arguments = sequence[len(results)]
                    delta = {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": f"call_{len(results)}",
                                "type": "function",
                                "function": {
                                    "name": "k8s_mcp_server__" + name,
                                    "arguments": json.dumps(arguments),
                                },
                            }
                        ],
                    }
                    finish = "tool_calls"
                else:
                    delta = {"role": "assistant", "content": scenario + " verified"}
                    finish = "stop"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for content, reason in ((delta, None), ({}, finish)):
                    chunk = {
                        "id": "fixture",
                        "object": "chat.completion.chunk",
                        "choices": [
                            {"index": 0, "delta": content, "finish_reason": reason}
                        ],
                    }
                    self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.close_connection = True

        return Handler


def wait_ready(url, process=None):
    with httpx.Client(trust_env=False, timeout=1) as client:
        for _ in range(100):
            if process and process.poll() is not None:
                raise RuntimeError("fixture service exited")
            try:
                if client.get(url).is_success:
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
    raise RuntimeError(f"fixture service not ready: {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-image", required=True)
    parser.add_argument("--server-binary", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if os.sys.flags.optimize:
        raise RuntimeError("assertions must be enabled")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    fixture = Fixture()
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.handler())
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    container = "daedalus-mcp-boundary-" + uuid.uuid4().hex[:10]
    process = None
    try:
        with (
            tempfile.TemporaryDirectory(prefix="daedalus-mcp-boundary-") as directory,
            contextlib.ExitStack() as stack,
        ):
            root = Path(directory)
            root.chmod(0o755)
            mcp_port, agent_port = port(), port()
            token = uuid.uuid4().hex
            kubeconfig = {
                "apiVersion": "v1",
                "kind": "Config",
                "current-context": "fixture",
                "clusters": [
                    {
                        "name": "fixture",
                        "cluster": {"server": f"http://127.0.0.1:{server.server_port}"},
                    }
                ],
                "contexts": [
                    {
                        "name": "fixture",
                        "context": {"cluster": "fixture", "user": "fixture"},
                    }
                ],
                "users": [{"name": "fixture", "user": {}}],
            }
            (root / "kubeconfig").write_text(yaml.safe_dump(kubeconfig))
            (root / ".kube").mkdir()
            (root / ".kube" / "config").write_text(yaml.safe_dump(kubeconfig))
            (root / "kubectl").write_text(
                '#!/bin/sh\nif [ "$1" = timeout ]; then exec /bin/sleep 3; fi\nprintf "partial output\\n"\nprintf "synthetic failure\\n" >&2\nexit 7\n'
            )
            (root / "kubectl").chmod(0o700)
            log = stack.enter_context(args.report.with_suffix(".server.log").open("w"))
            process = subprocess.Popen(
                [
                    str(args.server_binary.resolve()),
                    "--mode",
                    "streamable-http",
                    "--port",
                    str(mcp_port),
                    "--no-helm",
                    "--no-agent",
                    "--enable-kubectl",
                ],
                cwd=root,
                env={
                    "PATH": str(root),
                    "HOME": str(root),
                    "KUBECONFIG": str(root / "kubeconfig"),
                    "MCP_AUTH_TOKEN": token,
                    "MCP_REQUIRE_AUTH": "true",
                },
                stdout=log,
                stderr=log,
            )
            wait_ready(f"http://127.0.0.1:{mcp_port}/healthz", process)
            config = {
                "llms": {
                    "main": {
                        "model_name": "fixture",
                        "api_type": "chat",
                        "api_key": "fixture",
                        "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    }
                },
                "workflow": {
                    "_type": "daedalus_rust_agent",
                    "llm_name": "main",
                    "tools": ["k8s_mcp_server"],
                    "max_iterations": 8,
                    "instructions": "Verify results; preserve failures and partial effects.",
                },
                "function_groups": {
                    "k8s_mcp_server": {
                        "_type": "per_user_mcp_client",
                        "server": {
                            "url": f"http://127.0.0.1:{mcp_port}/mcp",
                            "custom_headers": {"Authorization": "Bearer " + token},
                        },
                        "include": [
                            "deleteResource",
                            "listResources",
                            "runKubectlCommand",
                        ],
                        "approval_policy": "auto_approve",
                    }
                },
            }
            (root / "config.yaml").write_text(yaml.safe_dump(config))
            (root / "config.yaml").chmod(0o644)
            command = [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                container,
                "--network",
                "host",
                "--entrypoint",
                "/workspace/daedalus-runtime",
                "-v",
                f"{root}/config.yaml:/workspace/config.yaml:ro",
            ]
            env = {
                "DAEDALUS_INTERNAL_API_TOKEN": token,
                "DAEDALUS_HOST": "127.0.0.1",
                "DAEDALUS_PORT": str(agent_port),
                "DAEDALUS_PREPARATION": "rust",
                "DAEDALUS_AUTHORIZATION": "rust",
                "DAEDALUS_TOOL_EXECUTOR": "disabled",
                "DAEDALUS_MEMORY_MODE": "disabled",
                "REDIS_URL": "redis://127.0.0.1:1",
            }
            for key, value in env.items():
                command += ["-e", key + "=" + value]
            subprocess.run(
                [*command, args.agent_image], check=True, stdout=subprocess.DEVNULL
            )
            wait_ready(f"http://127.0.0.1:{agent_port}/health")
            with httpx.Client(trust_env=False, timeout=30) as client:
                for scenario in (
                    "DELETE_STATES",
                    "REJECTED",
                    "KUBECTL_FAILED",
                    "KUBECTL_TIMEOUT",
                    "READ_ONLY",
                ):
                    response = client.post(
                        f"http://127.0.0.1:{agent_port}/v1/chat/completions",
                        headers={
                            "x-daedalus-internal-token": token,
                            "x-user-id": "fixture",
                        },
                        json={
                            "stream": True,
                            "messages": [{"role": "user", "content": scenario}],
                        },
                    )
                    response.raise_for_status()
                    assert scenario + " verified" in response.text, (
                        fixture.model_errors,
                        response.text,
                    )
                    assert not fixture.model_errors, fixture.model_errors
            assert fixture.deletes == [
                "/api/v1/namespaces/fixture/pods/sample",
                "/api/v1/namespaces/fixture/pods/forbidden",
            ], fixture.deletes
            assert fixture.reads == 3, fixture.reads
            args.report.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "agent_image": args.agent_image,
                        "server_binary": str(args.server_binary.resolve()),
                        "scenarios": 5,
                        "delete_requests": len(fixture.deletes),
                        "verification_reads": fixture.reads,
                        "model": "deterministic fixture; model wording quality unmeasured",
                    },
                    indent=2,
                )
                + "\n"
            )
            print(args.report.read_text())
    finally:
        logs = subprocess.run(
            ["docker", "logs", container], capture_output=True, text=True
        )
        args.report.with_suffix(".agent.log").write_text(logs.stdout + logs.stderr)
        subprocess.run(
            ["docker", "rm", "-f", container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if process:
            process.terminate()
            process.wait(timeout=10)
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
