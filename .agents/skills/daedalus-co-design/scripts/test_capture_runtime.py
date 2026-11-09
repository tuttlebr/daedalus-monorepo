"""Offline behavioral checks; no Kubernetes or provider calls."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "capture_runtime", Path(__file__).with_name("capture_runtime.py")
)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def pod(name, restarts=0):
    return {
        "metadata": {"name": name, "uid": "synthetic-uid"},
        "spec": {"containers": [
            {"name": "app", "image": "fixture", "env": [
                {"name": "PRIVATE", "value": "must-not-persist"}
            ]},
            {"name": "sidecar", "image": "fixture"},
        ]},
        "status": {"phase": "Running", "containerStatuses": [
            {"name": "app", "restartCount": restarts, "imageID": "sha256:fixture"}
        ]},
    }


class CaptureTest(unittest.TestCase):
    def run_capture(self, root, pods, fail_previous=False, extra=(), log=b"timestamp event\n"):
        calls = []

        def fake_command(argv, timeout, cwd=None):
            calls.append(argv)
            self.assertGreater(timeout, 0)
            if argv[0] == "git":
                return 0, b"fixture-sha\n" if "rev-parse" in argv else b"", b""
            self.assertEqual(argv[:6], ["kubectl", "--context", "fixture-context",
                                       "--namespace", "daedalus", "--request-timeout=15s"])
            if "get" in argv:
                return 0, json.dumps({"items": pods}).encode(), b""
            self.assertIn("logs", argv)
            self.assertTrue(any(arg.startswith("--limit-bytes=") for arg in argv))
            self.assertTrue(any(arg.startswith("--since-time=") for arg in argv))
            if fail_previous and "--previous=true" in argv:
                return 1, b"", b"previous container unavailable"
            return 0, log, b""

        output = io.StringIO()
        old_mask = os.umask(0o077)
        try:
            with patch.object(capture, "ROOT", root), patch.object(capture, "command", fake_command), \
                    patch.object(sys, "argv", ["capture", "--context", "fixture-context",
                                               "--pod-prefix", "switchyard-", *extra]), \
                    contextlib.redirect_stdout(output):
                code = capture.main()
        finally:
            os.umask(old_mask)
        result = json.loads(output.getvalue())
        directory = Path(result["output"])
        manifest = json.loads((directory / "manifest.json").read_text())
        return code, directory, manifest, calls

    def test_replicas_containers_previous_and_private_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, directory, manifest, calls = self.run_capture(
                Path(tmp), [pod("switchyard-a", 1), pod("switchyard-b"), pod("unrelated")]
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(manifest["pods"]), 2)
            logs = [c for c in calls if "logs" in c]
            self.assertEqual(len(logs), 5)
            self.assertEqual(sum("--previous=true" in c for c in logs), 1)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertFalse((directory / "pod-discovery.stdout").exists())
            for file in directory.iterdir():
                self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
                self.assertNotIn("must-not-persist", file.read_text())

    def test_partial_failure_preserves_success_and_reports_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, directory, manifest, _ = self.run_capture(
                Path(tmp), [pod("switchyard-a", 1)], fail_previous=True)
            self.assertEqual(code, 2)
            self.assertTrue((directory / "switchyard-a--app--current.stdout").read_bytes())
            self.assertTrue(any("Command failed" in g for g in manifest["gaps"]))

    def test_sandbox_provenance_and_explicit_log_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "submodules/daedalus-sandbox/tooling/verify.py"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"synthetic checker source\n")
            code, _, manifest, calls = self.run_capture(
                root, [pod("switchyard-a"), pod("llm-sandbox-a")],
                extra=("--pod-prefix", "llm-sandbox-"))
            self.assertEqual(code, 0)
            self.assertEqual(manifest["source"]["submodules/daedalus-sandbox"],
                             {"head": "fixture-sha", "status": ""})
            self.assertEqual(manifest["source_sha256"][str(path.relative_to(root))],
                             hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertTrue(any("logs" in c and "llm-sandbox-a" in c for c in calls))

    def test_bounds_and_missing_scope_are_not_passes(self):
        for pods, extra, expected in (
            ([], (), "No matching pods"),
            ([pod("switchyard-a"), pod("switchyard-b")], ("--max-pods", "1"), "Pod limit"),
            ([pod("switchyard-a")], ("--tail", "1"), "possible truncation"),
        ):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                code, _, manifest, _ = self.run_capture(Path(tmp), pods, extra=extra)
                self.assertEqual(code, 2)
                self.assertTrue(any(expected in g for g in manifest["gaps"]))

    def test_empty_logs_are_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, manifest, _ = self.run_capture(Path(tmp), [pod("switchyard-a")], log=b"")
            self.assertEqual(code, 2)
            self.assertTrue(any("No logs" in g for g in manifest["gaps"]))

    def test_command_timeout_is_bounded_and_reported(self):
        code, _, error = capture.command(
            [sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.05)
        self.assertEqual(code, 124)
        self.assertIn(b"Capture timeout", error)

    def test_total_deadline_prevents_further_cluster_reads(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(capture.time, "monotonic", side_effect=[0, 2]):
            code, _, manifest, calls = self.run_capture(
                Path(tmp), [pod("switchyard-a")], extra=("--budget-seconds", "1"))
            self.assertEqual(code, 2)
            self.assertTrue(any("Budget exhausted" in g for g in manifest["gaps"]))
            self.assertFalse(any(c[0] == "kubectl" for c in calls))


if __name__ == "__main__":
    unittest.main()
