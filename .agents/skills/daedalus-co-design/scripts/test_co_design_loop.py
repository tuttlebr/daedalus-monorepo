"""Deterministic tests of recursive feedback, evaluation gates and secret boundaries."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import co_design_loop as loop

ROUTES = sorted((loop.ROOT / "submodules/daedalus-switchyard").glob("routes_*.toml"))
SOURCE = loop.compose_routes(ROUTES[0])  # Offline fixture only; live runs require --routes.


def row(correct=True, seconds=10, tokens=10, route=True):
    return {
        "case": "task",
        "repeat": 0,
        "correct": correct,
        "seconds": seconds,
        "route_ok": route,
        "usage": {"total_tokens": tokens},
    }


class LoopTests(unittest.TestCase):
    def test_composition_snapshots_includes_without_rendering_or_writing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "parts").mkdir()
            fragment = root / "parts/client.toml"
            fragment.write_text(
                '[llm_clients.synthetic]\nbase_url = "http://localhost/v1"\n'
                'extra_headers = { affinity = "${PRIVATE_AFFINITY}" }\n'
            )
            profile = root / "routes.toml"
            original = 'include = ["parts/client.toml"]\nschema_version = 1\n'
            profile.write_text(original)
            first = loop.compose_routes(profile)
            self.assertNotIn("include", loop.tomllib.loads(first))
            self.assertIn("${PRIVATE_AFFINITY}", first)
            fragment.write_text(fragment.read_text().replace("localhost", "127.0.0.1"))
            self.assertNotEqual(loop.digest(first), loop.digest(loop.compose_routes(profile)))
            self.assertEqual(profile.read_text(), original)
            fragment.write_text('include = ["../routes.toml"]\n')
            with self.assertRaisesRegex(ValueError, "include cycle"):
                loop.compose_routes(profile)

    @unittest.skipUnless(os.environ.get("SWITCHYARD_TEST_BINARY"), "requires built gateway")
    def test_every_provider_starts_with_isolated_synthetic_credentials(self):
        for path in ROUTES:
            with self.subTest(provider=path.name), tempfile.TemporaryDirectory() as directory:
                source = loop.sandbox_routes(
                    loop.compose_routes(path), "http://127.0.0.1:1/v1", "http://127.0.0.1:2/v1"
                )
                with loop.gateway(
                    os.environ["SWITCHYARD_TEST_BINARY"], source, Path(directory), loop.Budget(1, 25)
                ) as url:
                    self.assertTrue(url.startswith("http://127.0.0.1:"))

    def test_native_responses_relay_preserves_wire_and_strips_credentials(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        seen = []
        payload = b'event: response.completed\ndata: {"type":"response.completed"}\n\n'

        class Peer(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                seen.append((self.path, dict(self.headers), json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        peer = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
        thread = threading.Thread(target=peer.serve_forever, daemon=True)
        thread.start()
        try:
            body = {"model": "daedalus/low", "input": "Synthetic", "reasoning": {"effort": "medium"}}
            with loop.Relay(f"http://127.0.0.1:{peer.server_port}/v1", loop.Budget(1, 5), 2) as relay:
                status, _, data = loop.wire(
                    relay.url + "/responses", body,
                    {"x-probe-relay-token": relay.token, "Authorization": "Bearer private", "x-request-id": "native-probe"}, 2,
                )
                self.assertEqual((status, data), (200, payload))
                self.assertEqual(seen[0][0], "/v1/responses")
                self.assertEqual(seen[0][2], body)
                headers = {key.lower(): value for key, value in seen[0][1].items()}
                self.assertNotIn("authorization", headers)
                self.assertNotIn("x-probe-relay-token", headers)
                self.assertEqual(headers["x-switchyard-request-id"], "native-probe")
                self.assertEqual(relay.records[0]["reasoning_effort"], "medium")
        finally:
            peer.shutdown()
            peer.server_close()
            thread.join(timeout=2)

    def test_every_provider_supports_the_classifier_edit_contract(self):
        self.assertTrue(ROUTES)
        for path in ROUTES:
            with self.subTest(provider=path.name):
                source = loop.compose_routes(path)
                before = loop.tomllib.loads(source)
                self.assertEqual(set(before["routes"]["stage"]["classifier"]["choices"]), set(loop.CLASSIFICATIONS))
                for level in loop.CLASSIFICATIONS:
                    updated = loop.tomllib.loads(loop.apply_edit(source, {
                        "field": f"choices.{level}.criteria", "value": "Synthetic rule.", "reason": "test",
                    }))
                    self.assertEqual(updated["targets"], before["targets"])
                    self.assertEqual(updated["llm_clients"], before["llm_clients"])
                for level in ("medium", "xhigh"):
                    with self.assertRaises(ValueError):
                        loop.apply_edit(source, {"field": f"choices.{level}.criteria", "value": "Invalid", "reason": "test"})

    def test_streaming_relay_does_not_forward_credentials_or_accept_unauthorized_calls(
        self,
    ):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        seen = []

        class Peer(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                seen.append(dict(self.headers))
                data = (
                    b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\n'
                    b"data: [DONE]\n\n"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        peer = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
        thread = threading.Thread(target=peer.serve_forever, daemon=True)
        thread.start()
        try:
            budget = loop.Budget(1, 5)
            with loop.Relay(
                f"http://127.0.0.1:{peer.server_port}/v1", budget, 2
            ) as relay:
                url = relay.url + "/chat/completions"
                body = {"model": "daedalus/low", "messages": []}
                status, _, _ = loop.wire(url, body, {}, 2)
                self.assertEqual(status, 403)
                self.assertEqual(budget.calls, 0)
                stream = loop.Stream()
                status, _, _ = loop.wire(
                    url,
                    body,
                    {
                        "x-probe-relay-token": relay.token,
                        "x-request-id": "test-call",
                        "Authorization": "Bearer synthetic-app-secret",
                    },
                    2,
                    stream.feed,
                )
                self.assertEqual(status, 200)
                self.assertTrue(stream.complete)
                self.assertEqual(stream.text, "OK")
                self.assertEqual(budget.calls, 1)
                headers = {k.lower(): v for k, v in seen[0].items()}
                self.assertNotIn("authorization", headers)
                self.assertNotIn("x-probe-relay-token", headers)
                self.assertEqual(headers["x-switchyard-request-id"], "test-call")
                status, _, _ = loop.wire(
                    url, body, {"x-probe-relay-token": relay.token}, 2
                )
                self.assertEqual(status, 502)
                self.assertEqual(len(seen), 1)
        finally:
            peer.shutdown()
            peer.server_close()
            thread.join(timeout=2)

    def test_classifier_evidence_requires_exact_call_id(self):
        with tempfile.TemporaryDirectory() as path:
            log = Path(path) / "gateway.log"
            log.write_text(
                'correlation_id="call-1" event="decision_api_classified" selected_target=low elapsed_ms=31\n'
            )
            rows = [
                {"attempt_ids": ["call-1"], "route_ok": True},
                {"attempt_ids": ["call-10"], "route_ok": True},
            ]
            loop.attach_gateway_evidence(log, rows)
            self.assertTrue(rows[0]["route_ok"])
            self.assertEqual(rows[0]["classifier_events"][0]["classifier_ms"], 31)
            self.assertFalse(rows[1]["route_ok"])

    def test_tool_probe_keeps_its_task_identity_across_distinct_model_calls(self):
        headers_seen = []

        def respond(url, body, headers, timeout, feed):
            headers_seen.append(headers)
            if len(headers_seen) == 1:
                delta = {"tool_calls": [{"index": 0, "id": "tool-1", "function": {
                    "name": "probe_value", "arguments": "{}"
                }}]}
                finish = "tool_calls"
            else:
                delta, finish = {"content": "OK"}, "stop"
            frame = json.dumps({"choices": [{"delta": delta, "finish_reason": finish}]})
            feed(("data: " + frame + "\n\ndata: [DONE]\n\n").encode())
            return 200, {}, b""

        client = loop.Client("http://127.0.0.1", loop.Budget(2, 10))
        case = {"id": "lookup", "split": "dev", "prompt": "Read", "answer": "OK", "tool": True}
        with patch.object(loop, "wire", respond):
            result, = loop.evaluate(client, [case], "run")
        self.assertTrue(result["correct"])
        first, follow = headers_seen
        self.assertEqual(first["x-switchyard-task-id"], follow["x-switchyard-task-id"])
        self.assertEqual(first["x-switchyard-session-id"], follow["x-switchyard-session-id"])
        self.assertNotEqual(first["x-switchyard-request-id"], follow["x-switchyard-request-id"])

    def test_user_turn_evidence_requires_one_initial_decision_and_a_reused_continuation(self):
        with tempfile.TemporaryDirectory() as path:
            log = Path(path) / "gateway.log"
            initial = 'correlation_id="open" event="decision_api_classified" selected_target=low elapsed_ms=31\n'
            repeated = 'correlation_id="tool" event="decision_api_classified" selected_target=low elapsed_ms=29\n'
            reused = 'correlation_id="tool" event="decision_api_reused" selected_target=low\n'
            for evidence, valid in [(reused, False), (initial + repeated, False), (initial + reused, True)]:
                with self.subTest(evidence=evidence):
                    log.write_text(evidence)
                    rows = [{"attempt_ids": ["open", "tool"], "route_ok": True}]
                    loop.attach_gateway_evidence(log, rows, "user_turn")
                    self.assertEqual(rows[0]["route_ok"], valid)
                    if valid:
                        self.assertEqual(len(rows[0]["classifier_events"]), 1)
                        self.assertEqual(rows[0]["routing_events"][1]["decision"], "reused")

    def test_transport_failure_does_not_prompt_for_policy_changes(self):
        def propose(*_):
            self.fail("Infrastructure failure must not trigger a model proposal")

        def evaluate(*_):
            return [{**row(False), "success": False}]

        with tempfile.TemporaryDirectory() as path, self.assertRaises(ValueError):
            loop.recursive_loop(
                SOURCE, [{}], [{}], propose, evaluate, Path(path), 2, 2, 0.15
            )

    def test_fixture_targets_must_exist_in_selected_route_configuration(self):
        loop.validate_case_targets([{"allowed": ["low", "high"]}], {"low", "high"})
        with self.assertRaisesRegex(ValueError, "unconfigured targets: medium"):
            loop.validate_case_targets([{"allowed": ["medium"]}], {"low", "high"})
        for name in ("probes.json", "probes-regression.json"):
            cases = loop.load_cases(
                Path(loop.__file__).parent.parent / "fixtures" / name
            )
            loop.validate_case_targets(cases, loop.tomllib.loads(SOURCE)["targets"])

    def test_edit_scope_and_validation(self):
        for field, value in [
            ("instructions", "New general policy.\nSecond line."),
            ("choices.low.criteria", "Literal extraction."),
            ("choices.low.min_probability", 0.7),
        ]:
            changed = loop.apply_edit(
                SOURCE, {"field": field, "value": value, "reason": "test"}
            )
            self.assertNotEqual(SOURCE, changed)
        for field, value in [
            ("base_url", "http://evil"),
            ("choices.none.criteria", "bad"),
            ("choices.low.min_probability", float("nan")),
            ("choices.low.min_probability", True),
            ("instructions", ""),
        ]:
            with self.assertRaises(ValueError):
                loop.apply_edit(
                    SOURCE, {"field": field, "value": value, "reason": "test"}
                )

    def test_stream_failures_cannot_pass_http_200(self):
        for tail in [
            "",
            'data: {"error":{"message":"bad"}}\n\n',
            "data: {broken\n\ndata: [DONE]\n\n",
        ]:
            stream = loop.Stream()
            stream.feed(
                b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\n'
            )
            stream.feed(tail.encode())
            self.assertFalse(stream.complete)
        stream = loop.Stream()
        stream.feed(
            b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\n'
        )
        stream.feed(b"data: [DO")
        stream.feed(b"NE]\n\n")
        self.assertTrue(stream.complete)
        self.assertEqual(stream.text, "OK")

    def test_quality_precedes_latency_and_unknown_usage_blocks_gain(self):
        base = [row()]
        for candidate in [
            row(False, 1),
            row(seconds=1, route=False),
            row(seconds=1, tokens=11),
            {**row(seconds=1), "usage": None},
            row(seconds=9),
        ]:
            self.assertFalse(loop.gate(base, [candidate], 0.15)[0])
        self.assertTrue(loop.gate(base, [row(seconds=8)], 0.15)[0])
        self.assertTrue(loop.gate([row(route=False)], [row()], 0.15)[0])
        self.assertFalse(loop.gate(base, [], 0.15)[0])

    def test_winner_and_rejections_feed_next_iteration_without_holdout(self):
        proposals = []

        def propose(source, feedback):
            proposals.append((source, feedback))
            i = feedback["iteration"]
            return {
                "field": "choices.low.criteria",
                "value": f"Policy {i}",
                "reason": "synthetic",
            }

        def evaluate(source, cases, label):
            if label.startswith("1-baseline-dev"):
                return [row(route=False)]
            if label.startswith("2-candidate-dev"):
                return [row(False)]
            return [row()]

        with tempfile.TemporaryDirectory() as path:
            best, history = loop.recursive_loop(
                SOURCE,
                [{"id": "dev"}],
                [{"id": "PRIVATE_HOLDOUT"}],
                propose,
                evaluate,
                Path(path),
                3,
                2,
                0.15,
            )
            self.assertEqual([r["accepted"] for r in history], [True, False, False])
            self.assertIn("Policy 1", proposals[1][0])
            self.assertEqual(proposals[1][0], proposals[2][0])
            self.assertEqual(
                proposals[2][1]["history"][-1]["reason"], "quality_or_routing_failed"
            )
            self.assertNotIn("PRIVATE_HOLDOUT", json.dumps([p[1] for p in proposals]))
            self.assertEqual(best, (Path(path) / "best.toml").read_text())

    def test_holdout_rejection_does_not_promote(self):
        def propose(*_):
            return {
                "field": "choices.low.criteria",
                "value": "Changed",
                "reason": "synthetic",
            }

        def evaluate(_source, _cases, label):
            return [
                row(
                    correct="candidate-holdout" not in label,
                    seconds=1 if "candidate" in label else 10,
                )
            ]

        with tempfile.TemporaryDirectory() as path:
            best, history = loop.recursive_loop(
                SOURCE, [{}], [{}], propose, evaluate, Path(path), 4, 1, 0.15
            )
            self.assertEqual(best, SOURCE)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["reason"], "holdout_gate_failed")
            self.assertFalse((Path(path) / "best.toml").exists())

    def test_budget_and_private_key(self):
        budget = loop.Budget(1, 5)
        budget.take()
        with self.assertRaises(loop.BudgetExhausted):
            budget.take()
        with tempfile.TemporaryDirectory() as path:
            key = Path(path) / "key"
            key.write_text("synthetic-key\n")
            key.chmod(0o644)
            with self.assertRaises(ValueError):
                loop.secret(key)
            key.chmod(0o600)
            self.assertEqual(loop.secret(key), "synthetic-key")

    def test_sandbox_has_only_explicit_upstream_aliases(self):
        for path in ROUTES:
            with self.subTest(provider=path.name):
                source = loop.sandbox_routes(
                    loop.compose_routes(path), "http://localhost:123/v1", "http://localhost:456/v1"
                )
                config = loop.tomllib.loads(source)
                self.assertEqual(set(config["targets"]), set(loop.tomllib.loads(loop.compose_routes(path))["targets"]))
                for level in config["targets"]:
                    self.assertEqual(config["targets"][level]["model"], "daedalus/" + level)
                for client in config["llm_clients"].values():
                    self.assertEqual(client["base_url"], "http://localhost:123/v1")
                    self.assertEqual(client["extra_headers"], {"x-probe-relay-token": "synthetic-test"})

    def test_correlation_does_not_join_timestamp_or_other_run(self):
        cid = "dc-" + "a" * 64
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            (root / "daedalus-backend-test--current.stdout").write_text(
                f'run_id="run-a" event="model_call_started" correlation_id="{cid}"\n'
            )
            (root / "switchyard-test--current.stdout").write_text(
                f'correlation_id="{cid}" event="decision_api_classified" selected_target=low\n'
            )
            rows = [
                {"call_id": "probe-a", "run_id": "run-a"},
                {"call_id": "probe-b", "run_id": "run-b"},
            ]
            results = loop.correlate(path, rows)
            self.assertTrue(results[0]["joined"])
            self.assertFalse(results[1]["joined"])
            self.assertEqual(results[0]["gateway"][0]["selected_target"], "low")


if __name__ == "__main__":
    unittest.main()
