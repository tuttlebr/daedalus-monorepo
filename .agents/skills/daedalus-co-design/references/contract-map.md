# Joint contract map

Paths below each root are relative to its submodule. Verify against current
code; this map locates evidence and does not override executable configuration.

The model path is agent -> Switchyard -> provider. The execution/verification
path is agent -> sandbox -> agent tool result -> model continuation. For the
agent/sandbox ownership map, source paths, and focused validation, read
[sandbox-contract.md](sandbox-contract.md) when that boundary is affected.

| Concern | Agent: `submodules/daedalus-agent` | Gateway: `submodules/daedalus-switchyard` | Joint check |
| --- | --- | --- | --- |
| Model intent and aliases | `protocol/model-profile.schema.json`, `backend/tool-calling-config.yaml`, `builder/runtime/src/preparation.rs`, `builder/runtime/src/agent.rs` | every discovered `routes_*.toml` | Resolved caller aliases exist; explicit intent survives default merging; automatic selection stays gateway-owned. |
| Provider wire/stream | `builder/runtime/src/provider.rs`, `builder/runtime/src/config.rs` | `patches/`, `Dockerfile` | Responses/Chat, terminal SSE, tool schema/results, reasoning history, usage, errors and retries agree on actual built artifacts. |
| Deployment/config | `helm/daedalus/`, `.env.example` | `charts/switchyard/`, `scripts/render_routes.py`, `scripts/deploy.sh` | Service/port, selected routes, environment substitutions, capabilities, image digest and runtime config match. |
| Request identity | `builder/runtime/src/provider.rs` | Header/transport patches and request logs | Distinguish correlation, run IDs, routing session, provider affinity and standard `user`; verify propagation. |
| Decision service | Complete model request and tool continuations | Decision patches, `docs/decision-input-limits.md`, `docs/standalone-decision-routing.md` | Input budgeting, media, discovery, deadline and fallback preserve answering-request semantics. |

## Source facts to recheck

- The main agent runtime is Rust. The Python routing helper and frozen
  `evaluation/model-routing/` reports do not establish current runtime behavior.
- Main endpoint/name come from environment-backed configuration. Autonomous
  requests can use a separate endpoint/model; not every request necessarily
  traverses Switchyard.
- The generic agent schema accepts six canonical effort labels; the shipped
  DeepSeek workflow configures only instant, low, high and max. Omission uses
  the configured main model; automatic routing is not an effort value. Retired
  `default`, `deep`, `deep_max`, and `none` values/config mappings are rejected, including
  stored jobs. Shipped request/skill promotions are unset. Reconcile older
  deployment overrides and queued requests before rollout.
- Discover provider variants with `routes_*.toml`; do not maintain a fixed filename
  list or choose a provider by glob order. Make/deploy/probe commands require an
  explicit source. New provider files are included automatically in contract tests
  and generated `deploy-route_<provider>` Make targets.
- All classifiers target four task categories: max, high, low and instant.
  Classifier prose, choices and the recursive learner must agree. Target names,
  fallback and explicit aliases remain provider-specific. A provider may expose
  extra passthrough levels without making them classifier categories.
- Inspect each selected target's model and body; public labels do not establish
  provider-native reasoning behavior or distinct settings. Preserve explicit
  aliases and provider payload defaults when changing only classification.
- Automatic routing uses `decision_api` on every request, including continuations.
  Do not assume sticky choice, a retained task floor or cross-provider failover.
  Read actual fallback targets from the selected TOML.
- Target IDs differ from provider model names. Caller fields can override shallow
  target defaults. An explicit alias alone does not prove the emitted effort.
- Selected TOML can differ from the chart example. Classifier prose/comments can
  lag executable fields; reconcile them when changing policy.

## Validation entry points

Read owning instructions, Makefiles and CLI options first. Choose focused checks
and the owning repository's required gates.

- Agent: provider unit tests, `builder/runtime_http_check.py` for actual Rust
  binary/image HTTP checks, `scripts/smoke_model_routing.py` for provider
  compatibility, `docs/rust-migration.md`, and `protocol/` for UI/runtime types.
  Inspect `make runtime` before use: it includes image/build work.
- Switchyard: `python3 -m unittest discover -s tests -v` from its root.
  `tests/test_provider_routes.py` discovers every provider file and checks the
  four-category contract and resolving aliases/targets. Use Python 3.11+ for `tomllib` (for example `uv run --python 3.12 --no-project python`).
  HTTP regressions in `tests/test_decision_api.py` and
  `tests/test_fireworks_chat_transport.py` need built artifacts; inspect
  `SWITCHYARD_TEST_BINARY` handling and report skips. `make validate` renders/lints
  selected routes/chart and may require header environment values; avoid exposing
  rendered values in public output.
- Switchyard `make test` is a **live model probe**, not the offline suite.
  `scripts/test_decision_judge.py` also probes a service. Inspect bounds/endpoints
  and authorization first. Deployment targets can build, publish and mutate the
  cluster; they are not validation-only commands.
- Neither suite alone proves the full path. For seam changes, exercise the built
  agent through the built gateway using deterministic synthetic provider/judge
  peers or an authorized isolated equivalent. If unavailable, state the missing
  end-to-end evidence instead of equating two mock suites with it.
- Parent `scripts/check_effort_boundary.py` (relative to this skill) exercises
  built agent -> gateway -> synthetic classifier/provider using selected route
  defaults and loopback endpoints. Pass `--routes` and both binary paths on a
  compatible host. The synthetic provider supports Chat transport (Fireworks
  and Baseten), not native OpenAI Responses.
  Covers automatic/explicit routing, tool continuation, classifier timeout,
  upstream retry, malformed tool rejection and retired profiles.
  It does not validate real provider capabilities, latency, or task quality.

- Parent `scripts/co_design_loop.py` and `scripts/test_co_design_loop.py` implement
  bounded recursive live policy trials, secure application probes, exact-ID
  log joins and deterministic quality/holdout gates. See `recursive-loop.md`.
- Agent `model_call_started.correlation_id` matches outbound `x-request-id` and
  `x-switchyard-request-id`. IDs are per logical model call; SDK transport retries
  retain the ID. Backend run IDs remain separate from opaque provider affinity.
