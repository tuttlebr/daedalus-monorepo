#!/usr/bin/env python3
"""Built agent runtime -> built context UniFi MCP server -> fixture controller.

Runs the agent's shipped `unifi_mcp_server` group, read from the workflow file,
against the real server binary. The controller is a local HTTPS fixture with
fixed latency and a throwaway certificate; the model is scripted: connect, list
sites, then site-scoped reads in one response: as many as the group's
`max_concurrency`, and at least four. It checks that every read returns its
own controller data and that the controller never sees more overlapping reads
than that bound (one when unset), and it reports the time the reads took.

Run it inside the agent image under test (the image supplies Python, PyYAML and
cryptography), loopback only:

    docker run --rm --network none \
        -v <this scripts directory>:/check:ro \
        -v <agent checkout>/backend:/workflow:ro \
        -v <directory holding the server binary>:/server:ro \
        -v <private output dir>:/out \
        --entrypoint python3 <agent-image> /check/check_unifi_mcp_boundary.py \
        --workflow /workflow/tool-calling-config.yaml \
        --server /server/unifi-network-mcp-server --report /out/<name>.json

Build the server for the image's platform from the context repository's
`unifi-network-mcp/src/Dockerfile` `builder` stage (the binary is
`/app/unifi-network-mcp-server`). No UniFi controller, credential, model
endpoint or cluster is used; a scripted model does not measure model behaviour.
"""

import argparse
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DELAY = 0.4
SITE = "11111111-2222-4333-8444-555555555555"
READS = {
    "listAdoptedDevices": ("devices", "fixture-device"),
    "listConnectedClients": ("clients", "fixture-client"),
    "listNetworks": ("networks", "fixture-network"),
    "listWifiBroadcasts": ("wifi/broadcasts", "fixture-broadcast"),
    "listWanInterfaces": ("wans", "fixture-wan"),
}
# The site reads one response proposes: (tool, offset). Set in main() from the
# shipped bound; a repeated tool pages with another offset so each call has
# its own controller data.
BATCH = []


def marker(name, offset):
    return f"{READS[name][1]}-o{offset}"

T0 = time.monotonic()
LOCK = threading.Lock()
CONTROLLER = {"in_flight": 0, "peak": 0, "requests": []}
MODEL = {"events": [], "failures": []}


def now():
    return round((time.monotonic() - T0) * 1000, 1)


class Controller(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        started = now()
        slow = f"/v1/sites/{SITE}/" in path
        if slow:
            with LOCK:
                CONTROLLER["in_flight"] += 1
                CONTROLLER["peak"] = max(CONTROLLER["peak"], CONTROLLER["in_flight"])
            time.sleep(DELAY)
            with LOCK:
                CONTROLLER["in_flight"] -= 1
        if path.endswith("/v1/info"):
            body = {"applicationVersion": "10.4.57"}
        elif path.endswith("/v1/sites"):
            body = {
                "offset": 0,
                "limit": 25,
                "count": 1,
                "totalCount": 1,
                "data": [{"id": SITE, "internalReference": "default", "name": "Default"}],
            }
        else:
            tool = next(
                (n for n, (suffix, _) in READS.items() if path.endswith(f"/{SITE}/{suffix}")),
                None,
            )
            if tool is None or self.headers.get("X-API-KEY") != "fixture-key":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            query = dict(
                pair.split("=", 1) for pair in self.path.partition("?")[2].split("&") if "=" in pair
            )
            offset = int(query.get("offset", 0))
            item = marker(tool, offset)
            body = {
                "offset": offset,
                "limit": 25,
                "count": 1,
                "totalCount": 9,
                "data": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, item)), "name": item}],
            }
        with LOCK:
            CONTROLLER["requests"].append({"path": path, "start": started, "end": now()})
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Model(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        received = now()
        results = {
            m["tool_call_id"]: m["content"] for m in body["messages"] if m["role"] == "tool"
        }
        rounds = [
            [("unifi_mcp_server__connect", {})],
            [("unifi_mcp_server__listSites", {})],
            [
                (
                    f"unifi_mcp_server__{name}",
                    {"siteId": SITE, "offset": offset} if offset else {"siteId": SITE},
                )
                for name, offset in BATCH
            ],
        ]
        done = 0
        for index, batch in enumerate(rounds):
            if all(f"c{index}_{i}" in results for i in range(len(batch))):
                done = index + 1
            else:
                break
        MODEL["events"].append({"kind": "request", "at": received, "round": done})
        problems = []
        if done >= 1 and "Connected" not in results["c0_0"]:
            problems.append("connect")
        if done >= 2 and SITE not in results["c1_0"]:
            problems.append("listSites")
        if done >= 3:
            for i, (name, offset) in enumerate(BATCH):
                text = results[f"c2_{i}"]
                expected = marker(name, offset)
                others = [marker(*call) for call in BATCH if call != (name, offset)]
                if expected not in text or any(other in text for other in others):
                    problems.append(f"{name}@{offset}")
                    MODEL["failures"].append(f"{name}@{offset}: {text[:300]!r}")
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
            chunk({"role": "assistant", "content": f"UNIFI FAILED {problems}"})
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
                                "function": {"name": name, "arguments": json.dumps(arguments)},
                            }
                        ]
                    }
                )
            chunk({}, "tool_calls")
        else:
            chunk({"role": "assistant", "content": "UNIFI verified"})
            chunk({}, "stop")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        MODEL["events"].append({"kind": "response", "at": now(), "round": done})
        self.close_connection = True


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait(url, process, headers=None):
    for _ in range(200):
        if process.poll() is not None:
            raise RuntimeError(f"process exited before {url} was ready")
        try:
            request = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(request, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"not ready: {url}")


def certificate(directory):
    """A throwaway self-signed certificate for the loopback controller."""
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import ipaddress

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(start + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    paths = os.path.join(directory, "cert.pem"), os.path.join(directory, "key.pem")
    with open(paths[0], "wb") as handle:
        handle.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(paths[1], "wb") as handle:
        handle.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, help="agent backend/tool-calling-config.yaml")
    parser.add_argument("--server", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--runtime", default="/workspace/daedalus-runtime")
    args = parser.parse_args()
    import yaml

    with open(args.workflow) as handle:
        workflow = yaml.safe_load(handle)
    shipped = {
        "group": workflow["function_groups"]["unifi_mcp_server"],
        "authentication": workflow["authentication"]["unifi_mcp_server"],
    }
    bound = int(shipped["group"].get("max_concurrency", 1))
    names = list(READS)
    BATCH.extend((names[i % len(names)], i // len(names)) for i in range(max(4, bound)))
    directory = tempfile.mkdtemp(prefix="unifi-joint-")
    args.cert, args.key = certificate(directory)

    controller = ThreadingHTTPServer(("127.0.0.1", 0), Controller)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(args.cert, args.key)
    controller.socket = context.wrap_socket(controller.socket, server_side=True)
    controller.daemon_threads = True
    threading.Thread(target=controller.serve_forever, daemon=True).start()
    model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    model.daemon_threads = True
    threading.Thread(target=model.serve_forever, daemon=True).start()

    mcp_port, agent_port, token = free_port(), free_port(), uuid.uuid4().hex
    logs = {name: open(os.path.join(directory, name + ".log"), "w") for name in ("server", "agent")}
    server = subprocess.Popen(
        [args.server, "--mode", "streamable-http", "--port", str(mcp_port)],
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": directory,
            "MCP_AUTH_TOKEN": token,
            "MCP_REQUIRE_AUTH": "true",
            "UNIFI_BASE_URL": f"https://127.0.0.1:{controller.server_port}",
            "UNIFI_API_KEY": "fixture-key",
            "UNIFI_FIXED_CONTROLLER": "true",
            "UNIFI_INSECURE_SKIP_VERIFY": "true",
        },
        stdout=logs["server"],
        stderr=logs["server"],
    )
    agent = None
    report = {"server": args.server, "runtime": args.runtime, "delay_ms": DELAY * 1000}
    try:
        wait(f"http://127.0.0.1:{mcp_port}/readyz", server)
        config = {
            "llms": {
                "main": {
                    "model_name": "fixture",
                    "api_type": "chat",
                    "api_key": "fixture",
                    "base_url": f"http://127.0.0.1:{model.server_port}/v1",
                }
            },
            "workflow": {
                "_type": "daedalus_rust_agent",
                "llm_name": "main",
                "tools": ["unifi_mcp_server"],
                "max_iterations": 8,
                "parallel_tool_calls": True,
                "instructions": "Use the proposed tools and report the result.",
            },
            "authentication": {"unifi_mcp_server": shipped["authentication"]},
            "function_groups": {"unifi_mcp_server": shipped["group"]},
        }
        path = os.path.join(directory, "config.yaml")
        with open(path, "w") as handle:
            json.dump(config, handle)
        agent = subprocess.Popen(
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
                # The shipped group reads its address and credential from these.
                "UNIFI_MCP_SERVER": f"http://127.0.0.1:{mcp_port}/mcp",
                "UNIFI_MCP_TOKEN": token,
            },
            stdout=logs["agent"],
            stderr=logs["agent"],
        )
        wait(f"http://127.0.0.1:{agent_port}/health", agent)
        request = urllib.request.Request(
            f"http://127.0.0.1:{agent_port}/v1/chat/completions",
            data=json.dumps(
                {"stream": True, "messages": [{"role": "user", "content": "UNIFI inventory"}]}
            ).encode(),
            headers={
                "content-type": "application/json",
                "x-daedalus-internal-token": token,
                "x-user-id": "fixture",
            },
        )
        started = now()
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8", "replace")
        finished = now()
        events = MODEL["events"]
        phases = [
            round(events[i + 1]["at"] - events[i]["at"], 1)
            for i in range(len(events) - 1)
            if events[i]["kind"] == "response" and events[i + 1]["kind"] == "request"
        ]
        site_requests = [r for r in CONTROLLER["requests"] if f"/{SITE}/" in r["path"]]
        checks = {
            "answer_verified": "UNIFI verified" in text,
            "no_fixture_failures": not MODEL["failures"],
            "model_requests": sum(e["kind"] == "request" for e in events) == 4,
            "every_site_read_once": len(site_requests) == len(BATCH),
            "bound_respected": CONTROLLER["peak"] <= bound,
        }
        report.update(
            {
                "passed": all(checks.values()),
                "checks": checks,
                "failures": MODEL["failures"],
                "group_max_concurrency": shipped["group"].get("max_concurrency"),
                "site_reads": len(BATCH),
                "latency_ms": round(finished - started, 1),
                "tool_phase_ms": phases,
                "controller_peak_in_flight": CONTROLLER["peak"],
                "controller_requests": CONTROLLER["requests"],
            }
        )
    finally:
        for process in (agent, server):
            if process:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
        for name, handle in logs.items():
            handle.close()
            with open(os.path.join(directory, name + ".log")) as source:
                with open(f"{args.report}.{name}.log", "w") as target:
                    target.write(source.read())
        with open(args.report, "w") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    print(
        json.dumps(
            {k: report.get(k) for k in ("passed", "checks", "site_reads", "tool_phase_ms", "controller_peak_in_flight", "group_max_concurrency")},
            indent=1,
        )
    )
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
