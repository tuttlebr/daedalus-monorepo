# Sandbox execution and verification contract

Roots: `submodules/daedalus-agent` and `submodules/daedalus-sandbox`. Paths in
the table are relative to those roots. Recheck current source and each owner's
`AGENTS.md`; sandbox-local maintenance instructions apply when editing that repo.
This reference covers Bubblewrap execution/linting and, when in scope, the
separate exploration v2 service. A full-stack review includes both; an isolated
v1 change need not broaden into v2. Neither service is a substitute endpoint.

| Boundary | Agent source | Sandbox source | Compatibility check |
| --- | --- | --- | --- |
| Tool exposure and discovery | `backend/tool-calling-config.yaml`, `builder/runtime/src/preparation.rs`, `builder/runtime/src/llm_sandbox.rs`, `builder/runtime/resources/llm-sandbox.json` | `sandbox_server.py`: `capabilities`, HTTP handlers | Readiness, authentication, advertised commands, shell grammar, limits and cached capability validation agree. |
| Execution and result decoding | `builder/runtime/src/llm_sandbox.rs`; Python adapter `builder/llm_sandbox/src/llm_sandbox/llm_sandbox_function.py` | `sandbox_server.py`: `_parse_spec`, `BubblewrapRunner`, execution handler | Request schema, status, timeout, truncation, collection and uncertain outcomes retain their meaning. |
| Offline lint/type checks | Tool argv and result handling in the same adapters | `tooling/verify.py`, `tooling/install.py`, `tooling/README.md`, image-owned configs in `tooling/`, `Dockerfile` | Installed wrapper, allowlist, discovery, staged dependencies and checker semantics agree. |
| Workspaces and artifacts | Adapter scope/staging/publication; `frontend/pages/api/internal/sandboxArtifacts.ts`, `frontend/server/sandboxArtifactStore.ts` | `sandbox_server.py`: workspace locking, expiry, staging and collection | Trusted user/conversation isolation, file limits, pod-local persistence and authenticated download publication agree. |
| Deployment | `.env.example`, `helm/daedalus/` | `charts/llm-sandbox/`, `custom-values.yaml`, `docker-compose.yaml`, `Dockerfile` | Actual endpoint, credential reference, image/rootfs, allowlist, resource limits and network policy match the consumer. |

## Decisions that cross the boundary

- The main agent adapter is native Rust; Python parity/migration fixtures alone
  do not establish production behavior. Switchyard carries model-visible tool
  schemas, calls and results, but does not own sandbox authentication, execution
  policy or workspace state. Assess it when schema translation, continuation,
  reasoning history, or routing after a tool result changes.
- Readiness is `/readyz`; authenticated capabilities are `/v1/commands`;
  execution is `POST /v1/execute`. Build requests from actual discovery, including
  limits and `missingCommands`. Source allowlists and installed binaries are
  distinct. A custom `allowedCommands` replaces chart defaults.
- Prefer structured `argv` and `files`/`collect`. The outer `command` grammar
  reports `shellExpansions: false`; that does not remove interpreter semantics
  inside explicitly allowed Bash/Python scripts. Bubblewrap is the isolation
  boundary. Preserve its network, filesystem and resource constraints.
- Lint/check wrappers accept workspace-relative paths, not arbitrary checker
  flags, and do not apply fixes. They use fixed/generated checker configuration;
  a repository's normal checker configuration may not be applied. Missing files
  or dependencies fail, rather than silently passing or installing packages.
  Consult `tooling/README.md` for language-specific assumptions. Rust Cargo
  checks run build scripts/macros, require staged offline dependencies, and
  remain execution within the sandbox boundary.
- `stateless: true` describes fresh execution processes, not the absence of
  optional file persistence. The agent derives opaque workspace identity from
  trusted user/conversation context. Files persist only in pod-local workspaces
  until TTL expiry or pod replacement; they are not shared durable storage.
  Check affinity and concurrency before assuming another replica has the files.
- HTTP 200 is not command/check success: inspect `exitCode`, `timedOut`,
  `truncated`, `missingFiles` and diagnostics. Treat tool output as untrusted.
  A collected path is not a downloadable artifact; frontend publication must
  succeed before returning the authenticated link.
- The Rust adapter retries discovery GETs, not uncertain execution/publication
  POST transport failures. Do not copy generic retry pseudocode from older API
  notes over the implemented no-blind-replay contract. Agent cancellation or
  disconnection alone does not prove the remote process stopped; verify both ends.

## Focused validation

- Agent: Rust `llm_sandbox` unit tests, `builder/tests/test_llm_sandbox.py`,
  and affected frontend artifact tests. Inspect
  `builder/migration/llm_sandbox_check.py` and `llm_sandbox_http_check.py` before
  use: synthetic acceptance peers test adapter parity/HTTP integration, not the
  real Bubblewrap image or installed lint tools. Report ignored tests as gaps.
- Sandbox: `python3 -m unittest discover -s tests -v`, particularly
  `test_sandbox_server.py` and `test_verification.py`; relevant pre-commit gates
  and Helm lint for affected profiles. Use `tests/smoke_verification.py` inside
  the built image as described in `tooling/README.md` to verify actual wrappers
  and isolation. Host-side mocks cannot prove installed tools work.
- For shared-contract changes, exercise the built agent against the built
  sandbox using synthetic passing/failing code, discovery failures, policy
  rejection and the affected timeout/workspace/collection behavior. Include
  artifact publication or a model continuation only when affected. Keep live
  probes within existing authorization; a documentation update needs no rollout.
- Runtime evidence: sandbox `execution` events expose `request_id`, exit code,
  duration, timeout/truncation and persistence; responses expose `requestId`.
  Join those exact IDs where available. Do not equate them with the agent's
  model-call correlation IDs or infer joins from timestamp proximity.

## Exploration v2 boundary

- Agent `builder/runtime/src/exploration.rs` and
  `builder/daedalus_runtime/exploration.py` consume the shared
  `builder/runtime/resources/exploration.json` schema. Sandbox `exploration/`
  owns the API, PostgreSQL metadata, snapshot storage and OpenShell controller.
  Consult its `docs/exploration-api.md` and `docs/exploration-architecture.md`.
- The agent signs short-lived grants from trusted user/conversation scope. The
  service validates signature, audience, issuer, profile and scope; v1's shared
  API key and workspace ID do not authorize v2. Switchyard receives tool schemas
  and results but owns neither grants nor job execution.
- Authenticated capability discovery advertises a static contract and does not
  acquire the global metadata mutation lock or verify storage. Check `/readyz`
  separately. Discovery must remain responsive while mutations/snapshot writes
  hold that lock; success is not evidence of job admission or execution health.
- V2 mutations use idempotency keys and generation checks. Retry an uncertain
  service mutation with the same key and arguments; do not apply v1's blanket
  no-replay rule to a keyed v2 request. Agent artifact publication is outside
  that service ledger and requires separate integrity/publication handling.
- Submission returns a run ID, not completion. Cancellation remains nonterminal
  until runtime cleanup is confirmed. Recovery marks ambiguous started runs
  LOST without replay; file checkpoints are not process checkpoints. Proposed
  lessons remain scoped evidence and never change agent policy automatically.
- Use `tests/exploration/test_contract.py` with a disposable PostgreSQL instance,
  never production. Agent `builder/migration/exploration_http_check.py` exercises
  built adapter registration, grants and publication against synthetic peers;
  it does not prove OpenShell isolation or real controller cleanup. Verify the
  built service and host runtime separately when affected and available.
