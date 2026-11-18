# Joint contract map

Paths below each root are relative to its submodule. Verify against current
code; this map locates evidence and does not override executable configuration.

The model path is agent -> Switchyard -> provider. The execution/verification
path is agent -> sandbox -> agent tool result -> model continuation. For the
agent/sandbox ownership map, source paths, and focused validation, read
[sandbox-contract.md](sandbox-contract.md) when that boundary is affected.
The information path is context ingestion/storage/retriever services -> agent
retrieval or MCP tool result -> model continuation through Switchyard. Read
[context-contract.md](context-contract.md) for its ownership, source paths and
validation. Hindsight is an external integration, not a fifth owned submodule.

| Concern | Agent: `submodules/daedalus-agent` | Gateway: `submodules/daedalus-switchyard` | Joint check |
| --- | --- | --- | --- |
| Model intent and aliases | `protocol/model-profile.schema.json`, `backend/tool-calling-config.yaml`, `builder/runtime/src/preparation.rs`, `builder/runtime/src/agent.rs` | every discovered `routes_*.toml` | Resolved caller aliases exist; explicit intent survives default merging; automatic selection stays gateway-owned. |
| Provider wire/stream | `builder/runtime/src/provider.rs`, `builder/runtime/src/provider/responses.rs`, `builder/runtime/src/config.rs` | `patches/`, `Dockerfile` | Responses/Chat, terminal SSE, tool schema/results, reasoning history, usage, errors and retries agree on actual built artifacts. |
| Deployment/config | `helm/daedalus/`, `.env.example` | `charts/switchyard/`, `scripts/render_routes.py`, `scripts/deploy.sh` | Service/port, selected routes, environment substitutions, capabilities, image digest and runtime config match. |
| Request identity | `builder/runtime/src/provider.rs` | Header/transport patches and request logs | Distinguish correlation, run IDs, routing session and standard `user`; verify propagation. Provider affinity is Switchyard's contract, set by the selected route file's `extra_headers`; the agent does not negotiate it per request. |
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
- Every shipped generation target requires `extra_body.stream = true`.
  Switchyard's required-streaming patch overrides explicit false as well as
  omitted stream controls. The agent's automation planning and direct model
  forwards request SSE; the frontend consumes planning SSE before draft validation.
  Auxiliary operations and the classifier remain separate non-generation APIs.
  Roll out the SSE consumer before the runtime/gateway; legacy direct JSON clients
  must migrate. This is the user's explicit streaming policy, not a generic
  recommendation for upstream Switchyard deployments.
- Retries exist at two layers. A gateway client retries twice before a response
  when `max_retries` is unset, and has no upstream deadline when `timeout_ms` is
  unset; no provider file sets either. The automatic route then tries
  `default_target`. The agent retries each failed attempt again. Count the
  product, not one setting. After a response starts only the agent retries, and
  only on the gateway's `upstream transport error: ` stream frame.

The agent architecture guide must describe standalone classification on every
model continuation. A stable session header is not evidence of sticky routing;
legacy Composite patches and frozen investigations do not define current routes.
For initial onboarding, compare generated environment output to real consumer
keys and Helm precedence, then verify the relevant protocol through the consumer.

## Deployment entrypoint contract

Each application exposes `make deploy` for current-checkout image publication
and in-place Kubernetes reconciliation, following the agent's existing pattern.
Respect component selection and saved local settings; Switchyard's explicit
provider choice may be persisted as `ROUTES_FILE` in `.env`. Do not choose a
provider implicitly. Validate settings before writes, pass freshly published
image references through to the workload, and preserve existing namespaces,
releases, PVCs, data and scoped credentials. Reconciliation of pinned upstream
images is distinct from building repository-owned code.

Test the public Make entrypoint with synthetic command peers, including settings
precedence, build/push failures, image freshness and absence of teardown commands.
A passing mock orchestration test does not prove a successful live rollout or
storage recovery. Inspect each owner's deployment instructions before invocation;
source-change authorization alone is not an instruction to execute deployment.

## Validation entry points

Read owning instructions, Makefiles and CLI options first. Choose focused checks
and the owning repository's required gates.

For optimization, use [experiment selection](optimization-loop.md) to match the
hypothesis to an evaluator. Agent `evaluation/tool-correctness/run.py` compares
real backend images or allowed workflow overlays through a real model and
isolated tools. `builder/migration/research_workflow_check.py` compares evidence
compaction/recovery through multi-stage tasks. These complement deterministic
boundary checks and the specialized classifier runner; they are not invoked
merely to validate a skill edit.

- Agent: provider unit tests, `builder/runtime_http_check.py` for actual Rust
  binary/image HTTP checks, `scripts/smoke_model_routing.py` for provider
  compatibility, `docs/rust-migration.md`, and `protocol/` for UI/runtime types.
  Inspect `make runtime` before use: it includes image/build work.
- Switchyard: `python3 -m unittest discover -s tests -v` from its root.
  `tests/test_provider_routes.py` discovers every provider file and checks the
  four-category contract and resolving aliases/targets. Use Python 3.11+ for `tomllib` (for example `uv run --python 3.12 --no-project python`).
  HTTP regressions in `tests/test_decision_api.py`,
  `tests/test_fireworks_chat_transport.py`, `tests/test_responses_transport.py`
  and `tests/test_stream_contract.py` need built artifacts; inspect
  `SWITCHYARD_TEST_BINARY` handling and report skips. The last one calls every
  route of every provider file through Chat and Responses with streaming on,
  off and omitted, and pins the mid-stream transport error frame.
  `make validate` renders/lints selected routes/chart and may require header
  environment values; avoid exposing rendered values in public output.
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
  compatible host. For a composed profile, first flatten the explicitly selected
  file with Switchyard `scripts/render_routes.py <profile> <temporary-output>
  --compose-only`, then pass that output to `--routes`. The synthetic provider
  speaks Chat and native Responses, so
  every current provider file can be selected.
  Covers automatic/explicit routing, tool continuation, classifier timeout,
  a transient upstream failure, a mid-stream upstream abort, the combined
  request count under persistent failure, malformed tool rejection, retired
  profiles and the streaming automation-planning forward with its
  correlation ID. A new retry layer or a changed gateway default fails the
  persistent-failure count; update `GATEWAY_RETRIES` only with source evidence.
  It does not validate real provider capabilities, latency, or task quality.
- Agent `frontend/e2e/tests/responses-accumulation.spec.ts` is the built
  gateway/runtime -> worker/Redis/WebSocket -> browser and public SDK check.
  Follow its `frontend/e2e/README.md` with an explicit backend image, gateway
  binary and native Responses profile. It shares the runtime fixture corpus
  and checks visible corrections, persisted text, reload, usage and failures.
  See agent `docs/responses-accumulation.md` for revision semantics and rollout
  order; old workers cannot consume backend snapshot replacements.
- Without a local Rust toolchain or on a non-Linux host, build both binaries in
  containers and run the check there. From the Switchyard root,
  `docker build --target builder -t <tag> .` leaves the gateway at
  `/opt/switchyard/target/release/switchyard-server`. Build the agent with
  `cargo build --locked --manifest-path builder/runtime/Cargo.toml` in a Rust
  1.95 container, mounting the agent read-only and `CARGO_TARGET_DIR` on a
  volume. Run this script and the Switchyard suite with
  `SWITCHYARD_TEST_BINARY` in a Linux image with Python 3.11+ and a libc at
  least as new as both builds. Locally built binaries are not the published
  images.

- Parent `scripts/test_context_boundary.py` resolves generated context settings
  against the real agent workflow under changed synthetic topology for both
  environments, and checks the agent template against served model IDs and the
  generated address of every context-owned MCP server the workflow registers.
  Run with Python 3.12, PyYAML and jsonschema. This configuration
  regression does not substitute for ingestion/retrieval through the built agent.
- Parent `scripts/test_model_alias_boundary.py` requires every alias the agent
  workflow defaults to, or its templates name (comments included), on every
  discovered provider file. Run with Python 3.12 and PyYAML. Offline only.
- Parent `scripts/route_source.py` delegates include composition to Switchyard's
  `scripts/render_routes.py`. The alias regression and recursive learner consume
  this standalone snapshot; they must not parse an include-only entrypoint as a
  complete routing policy. Private header environment values remain unresolved.
- Parent `scripts/co_design_loop.py` and `scripts/test_co_design_loop.py` implement
  bounded recursive live policy trials, secure application probes, exact-ID
  log joins and deterministic quality/holdout gates. See `recursive-loop.md` for
  this classifier-specific helper and `optimization-loop.md` for the broader
  agent-directed implementation and rollout cycle.
- Agent `model_call_started.correlation_id` matches outbound `x-request-id` and
  `x-switchyard-request-id`. Each agent attempt has its own ID; the gateway
  reuses it for its upstream retries and fallback target. Direct model forwards
  and automation planning log `model_forward_started` with an ID of the same
  form and an `origin`. Backend run IDs remain separate from opaque provider
  affinity.

## MCP call scheduling boundary

The agent owns scheduling; each MCP server owns its tolerance for sessions and
request bursts. Within one model response an MCP group runs its calls in
proposed order. Its `max_concurrency` (1 to 16; 16 when unset) bounds how many
tools whose configured policy is exactly `read_only` overlap; each overlapping
call uses its own session for that user, and every other operation, including
`__connect`, still runs alone. The agent also admits calls across runs through
a fair per-user, per-group semaphore in each backend process: reads take one
permit, exclusive calls take the group bound. A queued exclusive call prevents
later reads from passing it. This does not coordinate separate replicas or
guarantee that a timed-out remote operation has stopped. The heuristic mutation
detector does not grant overlap. One run executes at most 16 tool calls at once,
and the webscrape and source-verifier tools take the same `max_concurrency` range and fallback. A
group or tool stays serial only when it states 1. The Python MCP client ignores
the key and stays serial.

Mixed versions: the shared admission gate changes no wire or configuration
fields. Older runtimes lack cross-run read/write exclusion; mixed replicas do
not gain a distributed gate. Runtimes before agent `840a0454` ignore a group's key;
`840a0454` and earlier reject any `max_concurrency` above 8 at startup, for
groups and for the two tools. Roll the image and the workflow out and back
together. The shipped workflow states 16 on every group and both tools by user
direction; only the UniFi server has been exercised with overlapping reads.
Lower a group's bound when its server throttles bursts or limits sessions.

`scripts/check_mcp_read_overlap.py` (relative to this skill) runs inside an
agent image with networking disabled and checks ordering, exclusivity, bounds,
result binding and error/timeout isolation against a synthetic server, reporting
tool-phase time for paired comparisons; `--bound` (1 to 16) selects the fixture
bound, and its groups cover a stated bound, a stated 1 and an unset key.
`scripts/check_unifi_mcp_boundary.py` runs the shipped `unifi_mcp_server` group
against the built Context UniFi server and a fixture controller, proposing as
many site reads as the group's bound. Both use a scripted model: they establish
scheduling and delivery, not real-model behavior, live latency or provider
limits.

## Kubernetes MCP recovery boundary

The agent owns result interpretation; Context owns Kubernetes resource resolution
and tool execution. Neither Switchyard nor sandbox owns retries for this path.
Unqualified resources prefer core Kubernetes APIs, qualified names preserve
explicit group choice, and ambiguous non-core aliases fail. Tool execution
failures use MCP `isError`; RPC errors preserve bounded diagnostics in the agent.
Transport uncertainty still requires a state check, and no client automatically
replays mutations. A successful delete response means accepted, not absent.

After building the agent backend image and Context's Kubernetes MCP binary, run
`scripts/check_kubernetes_mcp_boundary.py` (relative to this skill) with
`--agent-image`, `--server-binary`, and `--report`. It starts both artifacts against
an isolated API and command fixture, covering core-versus-metrics resolution,
asynchronous deletion, explicit rejection, command failure/timeout, and a read-only
request. It uses no production kubeconfig or model endpoint. The agent's
`builder/runtime_http_check.py` additionally covers legacy RPC rejection through
both preparation modes. Synthetic continuation checks establish evidence delivery,
not real-model wording quality or deployed behavior. Server and client changes
can roll independently: older clients already understand MCP `isError`, while
new clients retain legacy RPC errors. No endpoint, permission, or schema migration
is required.
