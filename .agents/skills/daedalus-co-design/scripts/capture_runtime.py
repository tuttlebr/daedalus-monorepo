#!/usr/bin/env python3
"""Bounded, read-only Kubernetes evidence capture. Raw output stays Git-ignored."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[4]
SOURCE_REPOS = (
    ".", "submodules/daedalus-agent", "submodules/daedalus-switchyard",
    "submodules/daedalus-sandbox", "submodules/daedalus-context",
)
DEFAULT_PREFIXES = (
    "daedalus-backend-", "switchyard-", "decision-api-",
    "daedalus-autonomous-agent-", "daedalus-frontend-stream-worker-",
)


def utc_now():
    return datetime.now(timezone.utc)


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def command(argv, timeout, cwd=None):
    try:
        result = subprocess.run(
            argv, cwd=cwd, capture_output=True, timeout=timeout, check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or b"", (exc.stderr or b"") + b"\nCapture timeout\n"
    except OSError as exc:
        return 127, b"", str(exc).encode()


def source_state(path):
    result = {}
    for key, args in (
        ("head", ["rev-parse", "HEAD"]),
        ("status", ["status", "--short"]),
    ):
        code, out, _ = command(["git", "-C", str(path), *args], 5)
        result[key] = out.decode(errors="replace").strip() if code == 0 else None
    return result


def pod_summary(pod):
    spec, status = pod.get("spec", {}), pod.get("status", {})
    containers = []
    for key, status_key in (
        ("containers", "containerStatuses"),
        ("initContainers", "initContainerStatuses"),
    ):
        states = {item["name"]: item for item in status.get(status_key, [])}
        for item in spec.get(key, []):
            state = states.get(item["name"], {})
            containers.append({
                "name": item["name"], "kind": key, "image": item.get("image"),
                "image_id": state.get("imageID"),
                "restart_count": state.get("restartCount", 0),
                "ready": state.get("ready", False),
            })
    configmaps = set()
    for volume in spec.get("volumes", []):
        if volume.get("configMap", {}).get("name"):
            configmaps.add(volume["configMap"]["name"])
        for item in volume.get("projected", {}).get("sources", []):
            if item.get("configMap", {}).get("name"):
                configmaps.add(item["configMap"]["name"])
    return {
        "name": pod["metadata"]["name"], "uid": pod["metadata"].get("uid"),
        "owners": pod["metadata"].get("ownerReferences", []),
        "phase": status.get("phase"), "containers": containers,
        "volume_configmaps": sorted(configmaps),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, help="explicit kube context")
    parser.add_argument("--since-minutes", type=positive, default=30)
    parser.add_argument("--tail", type=positive, default=500, help="lines per container")
    parser.add_argument("--limit-bytes", type=positive, default=262144,
                        help="maximum bytes per log request")
    parser.add_argument("--timeout", type=positive, default=15,
                        help="seconds per kubectl call")
    parser.add_argument("--budget-seconds", type=positive, default=180,
                        help="total Kubernetes collection deadline")
    parser.add_argument("--max-pods", type=positive, default=30)
    parser.add_argument("--pod-prefix", action="append",
                        help="repeat to replace default pod-name prefixes")
    args = parser.parse_args()
    os.umask(0o077)
    base = ROOT / ".artifacts" / "daedalus-co-design"
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    output = Path(tempfile.mkdtemp(prefix=utc_now().strftime("%Y%m%dT%H%M%SZ-"), dir=base))
    started = utc_now()
    since = (started - timedelta(minutes=args.since_minutes)).isoformat().replace("+00:00", "Z")
    prefixes = args.pod_prefix or list(DEFAULT_PREFIXES)
    manifest = {
        "started_utc": started.isoformat(), "context": args.context,
        "namespace": "daedalus", "since_time": since,
        "limits": vars(args), "pod_prefixes": prefixes, "commands": [],
        "gaps": [], "pods": [], "source": {}, "source_sha256": {},
        "raw_sensitive_logs": True,
        "coverage": "Bounded tails; timestamps cover request execution, not an atomic snapshot.",
    }
    for name in SOURCE_REPOS:
        manifest["source"][name] = source_state(ROOT / name)
        if any(value is None for value in manifest["source"][name].values()):
            manifest["gaps"].append(f"Source provenance unavailable: {name}")
    files = [ROOT / "submodules/daedalus-agent/backend/tool-calling-config.yaml"]
    files.extend(sorted((ROOT / "submodules/daedalus-switchyard").glob("routes_*.toml")))
    files.extend(ROOT / "submodules/daedalus-sandbox" / name for name in (
        "sandbox_server.py", "tooling/verify.py", "tooling/install.py", "Dockerfile",
        "charts/llm-sandbox/values.yaml",
    ))
    context_root = ROOT / "submodules/daedalus-context"
    for pattern in ("stack/*.yaml", "stack/environments/*.yaml", "stack/schemas/*.json"):
        files.extend(sorted(context_root.glob(pattern)))
    files.extend(context_root / name for name in (
        "Makefile", "docker-compose.yaml", "scripts/contextctl.py",
        "scripts/render_refresh_contract.py",
    ))
    for path in files:
        if path.is_file():
            manifest["source_sha256"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    deadline = time.monotonic() + args.budget_seconds
    kubectl = ["kubectl", "--context", args.context, "--namespace", "daedalus",
               f"--request-timeout={args.timeout}s"]

    def capture(label, arguments, retain=True):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            manifest["gaps"].append(f"Budget exhausted: {label}")
            return None
        code, out, err = command([*kubectl, *arguments], min(args.timeout, remaining))
        if retain:
            (output / f"{label}.stdout").write_bytes(out)
        (output / f"{label}.stderr").write_bytes(err)
        manifest["commands"].append({
            "label": label, "argv": [*kubectl, *arguments], "exit_code": code,
            "finished_utc": utc_now().isoformat(), "bytes": len(out),
            "sha256": hashlib.sha256(out).hexdigest(), "stdout_retained": retain,
        })
        if code:
            manifest["gaps"].append(f"Command failed ({code}): {label}")
            return None
        return out

    # Pod specs can contain literal env values: retain only the summary below.
    raw = capture("pod-discovery", ["get", "pods", "-o", "json"], retain=False)
    if raw is not None:
        try:
            pods = json.loads(raw)["items"]
            chosen = sorted(
                (p for p in pods if p["metadata"]["name"].startswith(tuple(prefixes))),
                key=lambda p: p["metadata"]["name"],
            )
            for prefix in prefixes:
                if not any(p["metadata"]["name"].startswith(prefix) for p in chosen):
                    manifest["gaps"].append(f"No matching pods: {prefix}")
            if len(chosen) > args.max_pods:
                manifest["gaps"].append("Pod limit reached; discovery coverage incomplete")
            manifest["pods"] = [pod_summary(p) for p in chosen[:args.max_pods]]
        except (ValueError, KeyError, TypeError) as exc:
            manifest["gaps"].append(f"Invalid pod discovery: {type(exc).__name__}")
    for pod in manifest["pods"]:
        for container in pod["containers"]:
            # Completed init logs usually precede this window; capture them only
            # when restarted. Ordinary containers always receive a current read.
            if container["kind"] == "initContainers" and not container["restart_count"]:
                continue
            modes = [False, True] if container["restart_count"] else [False]
            for previous in modes:
                label = f"{pod['name']}--{container['name']}--{'previous' if previous else 'current'}"
                arguments = ["logs", pod["name"], "--container", container["name"],
                             "--timestamps=true", f"--since-time={since}",
                             f"--tail={args.tail}", f"--limit-bytes={args.limit_bytes}"]
                if previous:
                    arguments.append("--previous=true")
                data = capture(label, arguments)
                if data == b"":
                    manifest["gaps"].append(f"No logs in bounded window: {label}")
                if data is not None and (len(data) >= args.limit_bytes or len(data.splitlines()) >= args.tail):
                    manifest["gaps"].append(f"Log bound reached; possible truncation: {label}")
    manifest["finished_utc"] = utc_now().isoformat()
    manifest["complete"] = not manifest["gaps"]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"output": str(output), "pods": len(manifest["pods"]),
                      "complete": manifest["complete"], "gaps": len(manifest["gaps"])}))
    return 0 if manifest["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
