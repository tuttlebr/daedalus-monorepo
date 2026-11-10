# Verified lessons and open questions

Keep current reusable knowledge, not a run transcript. Follow
[the evidence workflow](runtime-evidence.md) when revising entries.

## L011: the context stack exposes several consumer contracts, not one context API

- **Status:** verified source ownership and consumer configuration during initial
  skill onboarding; runtime was not verified. L012 adds the subsequent
  cross-consumer regression and fixes a generated-ingestion-settings omission.
- **Evidence:** context `ef90bcd2ec28ef12673bb887f200f0ed9724b823` and agent
  `1764e085c116e8cd618c1e6989416cad65d2a80c`. Context topology separates storage,
  embedding/reranking, ingestion and infrastructure MCP services; Hindsight is
  an external owner. `contextctl.agent_env` generates retrieval and MCP settings
  consumed by the agent workflow. Both checked-in environment contracts validate.
- **Action:** assess the affected service and agent consumer, distinguish
  embedding-space compatibility from dimension equality, and validate evidence
  metadata/freshness through retrieval. Keep provider, dependency/data and
  consumer health separate. Consult [context-contract.md](context-contract.md)
  for source ownership and checks; do not route context calls through Switchyard
  merely because model continuations use it.
- **Verification:** local contract validation and generated-key/consumer checks;
  collector regression covers fourth-repository provenance, contract hashes,
  selected context logs and exclusion of private environment content.
- **Limit:** source/schema checks do not establish deployed model or corpus
  state, retrieval quality, full-path performance or external Hindsight health.
  Runtime coverage requires the context owner's environment/context prerequisites.
- **Recheck:** topology/ownership, consumer environment generation, embedding
  space, collection aliases, endpoint shapes or health/permission semantics change.

## L001: source aliases are not effective runtime aliases

- **Status:** historical source-contract discrepancy; removed from current agent
  source by canonical-effort migration. Existing deployments remain unverified.
- **Condition:** an agent profile resolves to an alias absent from gateway routes.
- **Evidence:** at agent `22de3aa09cda884bb00e24da49d2154d4fd84848` and gateway
  `bbd186ebc1b8e27bb8c5799818c4bfdb5028bb7e`, a legacy profile default in
  `backend/tool-calling-config.yaml` has no public alias in either selectable TOML.
  Deployment environment overrides can replace that default.
- **Action:** resolve effective mappings and selected routes before declaring a
  live defect; reconcile profile choices, skill promotion, UI/protocol values and
  gateway aliases when migrating to the current user-approved contract.
- **Limit:** source inspection only; no failing production request or corrected
  joint-path test demonstrated during skill creation. Subsequent removal is
  covered by L005; historical evidence above is not a current source default.
- **Recheck:** mapping, environment defaults or route inventory changes.

## L002: sampled gateway telemetry does not establish agent provenance

- **Status:** verified bounded observation; traffic origin/cause unknown.
- **Evidence:** namespace `daedalus` sample on 2026-11-07 around 13:10:48–13:10:52
  UTC showed gateway Chat requests with empty correlation/session fields. A separate
  agent sample around 13:07–13:09 UTC logged run IDs and Responses calls. These
  are not established to be the same requests.
- **Action:** correlate propagated IDs or reproduce in isolation; do not attribute
  those gateway timings/selections to agent behavior by proximity.
- **Limit:** deployed source/config correspondence unverified; this does not show
  that the agent universally drops IDs.
- **Recheck evidence:** until L020 the agent's direct model forwards and
  automation planning sent Chat requests with no correlation header. That is one
  candidate source of such traffic; it is not established for this sample.
- **Recheck:** correlation coverage, transport, workload or instrumentation changes.

## L003: deployed route configuration can change the meaning of effort aliases

- **Status:** historical source/ConfigMap discrepancy reconciled at the newer
  checkout; active provider payloads remain unverified.
- **Condition:** diagnosing effort behavior from a checked-out route file.
- **Evidence:** on 2026-11-07 around 13:27 UTC, namespace `daedalus` ConfigMap
  `switchyard`, referenced by the discovered gateway pod, had route-content SHA-256
  `442abeec8d12026373a60c95e044a2e728c6a771f5d57a51741035f36d915aef`.
  Parsed model/body definitions for all six targets differed from both selectable
  TOMLs at gateway `bbd186ebc1b8e27bb8c5799818c4bfdb5028bb7e` (agent
  `22de3aa09cda884bb00e24da49d2154d4fd84848`). The ConfigMap mapped `high` to
  provider effort `low`, `xhigh` to `high`, and `instant` to `none`; neither source
  file nor that ConfigMap exposed a separate `daedalus/none` route.
- **Verification:** parsed the ConfigMap and both source TOMLs independently and
  compared target model/body fields; this is configuration evidence, not a live
  model regression or a claim about supported provider effort values.
- **Recheck:** on 2026-11-07 around 13:39 UTC, the same ConfigMap content hash
  matched all parsed targets and routes in the then-selected provider TOML at gateway
  `7250faaba434f18153ed2dd6c832156823087a1b`; agent remained at `22de3aa`.
  Independent parsed assertions confirmed identical provider configurations for
  `high`/`low` and `xhigh`/`medium` (excluding target IDs). Do not carry the old
  source-drift diagnosis forward or infer distinct provider effort from these
  public labels. Header rendering and process-loaded configuration remain separate.
- **Action:** pin route-content hashes as well as image digests before comparing
  behavior. Verify loaded configuration and actual synthetic upstream payloads
  before assigning provider semantics or migrating the agent's public choices.
- **Limit:** mounted-file/process reload state, effective agent environment and
  built-image/source correspondence were not established. No causal attribution
  of latency, quality or cost is supported.
- **Recheck:** configuration rollout/reload, route rendering, caller override or
  provider translation changes. The recorded mapping is evidence, not a default
  or recommendation.

## L004: selectable route variants need independent classifier consistency checks

- **Status:** historical source inconsistency, reconciled by the variant checks
  in L010; historical live impact unverified.
- **Evidence:** at gateway `7250faaba434f18153ed2dd6c832156823087a1b`, parsed
  `routes_openai.toml` contains only the OpenAI client, while its classifier
  instructions say all answering profiles use Fireworks/DeepSeek. Its `instant`
  criteria describe high effort although its target configures low effort.
- **Verification:** independent TOML assertions and source inspection; the
  stale-model assertion in `tests/test_fireworks_routes.py` checks only the custom
  variant. The offline probe-schema test also expects `xhigh` for both variants,
  contradicting the OpenAI variant's configured `medium` default.
- **Action:** check classifier prose, choice criteria and fallback expectations
  against each selectable variant's executable fields. Shared alias names do not
  imply shared provider semantics or fallback targets.
- **Limit:** the sampled deployed ConfigMap matches the custom variant. No
  misclassification or provider capability failure was demonstrated for OpenAI.
- **Recheck:** variant configuration, classifier prose or regression coverage changes.

## L005: automatic routing is omission, not an effort profile

- **Status:** verified source and built synthetic boundary contract.
- **Condition:** migrating clients, queued jobs or workflow configuration away
  from retired `default`, `deep`, `deep_max`, and `none` profiles.
- **Evidence:** 2026-11-07 removal work based on agent `22de3aa` and gateway
  `7250faa`. Generated schema, Rust/Python preparation and frontend validation
  accept canonical effort names and reject retired values. Shipped automatic
  request/skill promotion maps are removed; main route selection stays with the
  configured model and gateway.
- **Verification:** agent Rust/Python and frontend regressions; parent
  `scripts/check_effort_boundary.py` passed against the changed built agent and
  gateway image digest
  `0509fb5988d55490ae6db48928b67d018534fecd52c4c09e2d4d6fb94d73f073`.
  Fourteen synthetic cases cover automatic and six explicit routes, a tool
  continuation, classifier timeout, upstream retry, malformed tool rejection,
  retired values including `none`. Explicit routes bypass classification;
  automatic continuations reclassify. Rejected profiles never reach a provider.
- **Action:** omit `model_profile` for automatic routing; migrate configured
  mappings and API/stream workers together. Resubmit queued retired values with
  omission or a configured canonical effort. Preserve explicit selections.
- **User correction:** the follow-up instruction retired `none` as well. The
  schema and configuration now reject it rather than reserving an unconfigured
  seventh option. Provider-native `reasoning_effort = "none"` remains a separate
  wire value and does not expose a public profile.
- **Limit:** no deployment or real-provider capability claim. Synthetic upstream
  acceptance cannot establish provider support.
- **Recheck:** schema, preparation, alias inventory, worker validation or gateway
  routing/transport changes. Retain frozen baseline fixtures as historical evidence;
  do not rewrite them to imply the baseline supported the new contract.

## Q001: verify effective provider semantics

- **Status:** the target classifier contract is max/high/low/instant. Provider
  aliases, native reasoning settings and fallback remain separate contracts.
- **User direction:** on 2026-11-09 the user corrected the prior review: four
  classifications are intentional. Discover provider sources with `routes_*.toml`
  and align affected consumers as new providers are onboarded. Do not restore six
  categories based on historical guidance. Public `none` remains retired.
- **Next check:** verify selected-source versus loaded-route correspondence,
  caller overrides and actual provider payloads. Measure independent task quality,
  latency and cost before claiming a benefit from the four-category migration.

## L006: correlate logical model calls separately from transport attempts

- **Status:** verified built joint boundary; partial live joins observed.
- **Evidence:** 2026-11-07, agent based on `22de3aa`, gateway image
  `0509fb5988d55490ae6db48928b67d018534fecd52c4c09e2d4d6fb94d73f073`.
  Updated `check_effort_boundary.py` verifies opaque `dc-` IDs in agent
  `model_call_started`, gateway routing spans, and outgoing `x-request-id`.
  Fourteen automatic/explicit, continuation, failure and rejection cases pass.
- **Action:** join exact correlation IDs; scope them to backend run/model-call
  pairs. Every agent attempt, retry or continuation gets a new ID. A repeated
  ID at the provider is the gateway retrying upstream under the forwarded ID
  (L019), not an agent SDK retry as first recorded here. Count repeated upstream
  attempts separately; never infer a new agent call from another upstream request.
- **Limit:** a deployed application probe completes, but its older backend does
  not emit the new IDs. Full live joins require the changed agent image. Existing
  Switchyard support suffices; no gateway code rollout is needed for this header.
- **Recheck evidence:** 2026-11-09 11:59–12:29 UTC capture joined 12 of 16
  backend logical call IDs to gateway spans exactly. Gateway output reached the
  250-line bound; missing joins do not establish missing propagation. Traffic
  origin and deployed-image/source correspondence remain unverified. The earlier
  rollout gap is historical, not a claim that the current backend lacks IDs.
- **Recheck:** provider transport retry ownership, wire headers, run-ID generation,
  gateway metadata allowlist or logging changes.

## L007: recursive policy trials must separate routing criteria from answer quality

- **Status:** verified narrow live pilot; not a general quality/performance claim.
- **Evidence:** 2026-11-07 recursive learner, source agent `22de3aa`, gateway
  `7250faa` and the L006 gateway image, real decision service and LAN NodePort.
  Three bounded iterations issued 81 runner requests. One instruction candidate
  was retained locally; subsequent proposals were rejected. Exact-ID classifier
  events were found for all evaluated requests, including tool continuations.
- **Verification:** fixed synthetic development/holdout checks (four tasks each,
  two repeats). Routing acceptance improved 4/8 to 8/8 and 5/8 to 8/8 respectively;
  all answers were correct before and after. The candidate clarified mechanical
  tool-result relay and bounded dependency reasoning. Total development latency
  was 5.03s versus 5.11s; reported tokens 1465 versus 1599. Holdout latency was
  5.01s versus 5.08s; tokens 1716 versus 1913. No speed or cost win is established.
- **Action:** feed rejected results into the next proposal, retain the incumbent
  on failure, protect evaluators/holdout content, and stop at explicit limits.
  Require reverse-order confirmation before retaining a latency-only winner.
  Record outgoing profile/effort and actual classifier events, not just HTTP 200.
- **Limit:** allowed routing sets are design expectations, not independent proof
  of minimum sufficient effort. Tiny related holdouts are not broad quality
  evidence; adaptive holdout pass/fail feedback can overfit. Real provider
  internals and billed cost remain unknown. The candidate remains an ignored
  local artifact; no production policy or deployment was changed.
- **Recheck:** fresh independent tasks, changed provider/decision models, source
  policy, runtime provenance, load/cache conditions or evaluation gates.

## L008: version evaluation corrections independently of policy candidates

- **Status:** verified source-rubric inconsistency and bounded live reproduction.
- **Evidence:** 2026-11-07 follow-up, same agent/gateway source bases as L007.
  A fresh fixture required at least `medium` for executing a fixed arithmetic
  recurrence, although the existing low criteria allow basic arithmetic and
  mechanical transformations. Both attempts returned correct answers at `low`.
  Failed development runs were preserved, then a new fixture version permitted
  `low` before a fresh baseline. The answering task and expected integer stayed
  unchanged; no model proposal changed the evaluator.
- **Verification:** `fixtures/probes-regression.json`; retained L007 policy passed
  8/8 development and 8/8 independent holdout checks (two repeats). Two further
  proposals were rejected: no clear paired improvement, then invalid/unchanged
  proposal. The candidate development total was 5.96s versus 6.36s baseline,
  but the next unchanged baseline took 5.23s. These small aggregate differences
  do not establish a durable latency gain. Runtime images and mounted route
  ConfigMap hash stayed stable during the recursive comparison.
- **Action:** review routing expectations against task semantics, preserve failed
  evidence, and restart after an evaluator correction. Keep deterministic answer
  checks separate from policy-label agreement. Retain rejected proposals as
  feedback; do not force a new winner on each skill invocation.
- **Limit:** small related synthetic tasks and public-profile rubric agreement
  do not prove broad quality, provider effort necessity or cost savings. The
  prior policy remains local and undeployed. Live backend-to-gateway ID joins
  still require the agent correlation rollout.
- **Recheck:** classifier rubric, task deliverable, evaluation expectations,
  provider models, cache/load conditions or deployed images change.

## L009: expose provider settings separately from task-classification categories

- **Status:** verified historical source/boundary; current payload defaults have
  changed (L010). The separation of profiles and task categories still applies.
- **Evidence:** user selected four DeepSeek-only passthrough profiles on
  2026-11-07. Fireworks' Chat Completions reference maps DeepSeek V4.1 low to low,
  medium/high/xhigh to high, max to max, and none to reasoning disabled:
  https://docs.fireworks.ai/api-reference/post-chatcompletions . Historical L003
  six-target source mappings are superseded by this source change, not evidence
  that a deployed configuration has already changed.
- **Historical mapping:** custom public profiles were instant/low/high/max,
  requesting none/low/high/max in that Fireworks configuration. The later user
  correction in Q001 sets four classifier categories; preserve the distinction
  from explicit profiles and provider effort. The historical migration removed
  duplicate medium/xhigh custom aliases; it migrated those callers to high or automatic.
  Generic agent validation can retain other levels for other provider variants;
  the shipped workflow exposes only configured custom profiles.
- **Verification:** actual built agent/gateway boundary (14 cases), seven gateway
  configuration/wire checks, 72 agent Python checks, 22 capability-gate checks,
  and 12 recursive-runner checks. Capability reports now list every covered
  target and explicit alias while probing each unique provider configuration once.
  A second live recursive run retained a local candidate with 8/8 development
  and holdout answer/routing checks after fixture target names were migrated.
- **Limit:** fixture expectations must name concrete targets, not removed task
  labels. The pre-migration live run is preserved and is not a routing-quality
  comparison. Corrected candidate development/holdout totals were 4.46s/5.31s
  versus 4.12s/4.87s baseline; no speed or cost win is claimed. Candidate tuning
  remains an ignored local artifact. Source changes require deployment; old
  high aliases requested low, so mixed rollout semantics must be documented.
- **Recheck:** provider family or effort normalization, public inventory,
  task-to-target mappings, deployment configuration or suite changes. The
  November 6 multi-model benchmark cannot justify a same-model effort inversion.

## L010: discover provider variants and align to the current user contract

- **Status:** verified route-consumer drift; prior six-category recommendation
  superseded by explicit user correction on 2026-11-09.
- **Evidence:** gateway `d434e0c`, agent `1764e08`, sandbox `cc072ea`.
  Splitting the provider configuration left a deleted filename in Make/deploy
  defaults, tests and docs; the five-test route suite failed on that missing file.
  The sampled live ConfigMap matched Baseten targets/routes and four categories.
  The previous review wrongly treated four categories as a defect by following
  stale instructions. The user clarified the intended four-category contract.
- **Action:** discover every `routes_*.toml`, validate max/high/low/instant
  classifier choices and prose, and require explicit source selection for live
  operations. Align source, tests, helpers and docs within the requested work.
  Keep explicit aliases, fallback targets and native effort settings separate;
  do not equate a profile name with measured provider capability.
- **Regression:** provider contract tests and parent learner tests now discover
  the complete glob. Learner edits are limited to the four categories; existing
  provider targets, native payloads, explicit aliases and retained gates are
  preserved. The deleted filename is no longer an active input or default.
- **Built verification:** synthetic agent -> gateway -> judge/provider checks
  passed all four automatic choices, explicit profiles, tool continuation,
  timeout, retry and rejection cases for both Chat variants. All discovered
  provider files passed the built gateway's configuration validation. Native
  Responses end-to-end coverage and live quality comparison remain separate.
- **Limit:** frozen investigation records retain historical filenames and values
  as provenance. Offline contract checks do not establish provider capability,
  task quality, latency or cost; rollout and matched trials remain separate.
- **Recheck:** provider onboarding, user contract changes, route inventory,
  classifier choices, consumers, loaded configuration or wire defaults change.

## L012: generated service settings must match consumer keys and precedence

- **Status:** verified source integration defect with synthetic regression.
- **Evidence:** context `ef90bcd`, agent `1764e08`, reviewed 2026-11-09.
  Context generated only `NV_INGEST_ENDPOINT`; Rust/Python ingestion and workflow
  YAML consume `NV_INGEST_HOST` and `NV_INGEST_PORT`. Local context schema
  validation passed despite this omission. The generator now emits both forms.
- **Verification:** context's changed-topology test fails on the old generator;
  parent `scripts/test_context_boundary.py` resolves the actual agent workflow
  from both generated environments, including ingestion, embedding, retrieval
  and reranking settings. Synthetic HTTP probe tests also verify both native
  role-aware messages and NIM input/input_type without a duplicated query prefix,
  and reject invalid vectors even when dimensions match.
- **Action:** validate generated keys against real consumers. Reconcile agent
  Helm `retrieval.*` values separately: enabled retrieval filters duplicate
  Milvus/readiness keys from generic backend environment overrides. Separate
  provider reachability/protocol probes from actual agent retrieval and citations.
- **Limit:** no live corpus, embedding revision, full ingestion/retrieval
  continuation or deployed configuration acceptance was established. Context
  cluster collection lacked its required local environment file.
- **Recheck:** generator, agent settings, Helm precedence, role templates,
  embedding space or collection contracts change.

## L013: exploration discovery must not wait behind durable mutations

- **Status:** verified implementation and authenticated HTTP regression.
- **Evidence:** sandbox `cc072ea`, agent `1764e08`, reviewed 2026-11-09.
  Static v2 capabilities previously entered the same PostgreSQL mutation lock
  as snapshot operations. Discovery now validates auth/arguments then returns
  the static contract without acquiring storage or the mutation lock.
- **Verification:** real FastAPI GET/POST handlers with signed synthetic grants
  pass with storage unavailable; invalid grants/arguments still fail and
  readiness remains unavailable. All 16 exploration contracts pass against
  disposable PostgreSQL, including concurrent keyed submission and scope checks.
- **Action:** distinguish static discovery, dependency readiness, job completion
  and runtime cleanup. Preserve v1's no-blind-replay execution contract while
  retaining v2 same-key/same-arguments retries for ledger-backed mutations.
- **Limit:** no measured production latency gain, real OpenShell/Bubblewrap
  execution or built agent-to-service path in this run. The fix removes a
  lock/storage dependency, not a demonstrated end-to-end performance bottleneck.
- **Recheck:** advertised capabilities become storage-dependent, grants/schema,
  mutation locking, idempotency ledger or controller recovery changes.

## L014: transport-specific defaults need separate wire regressions

- **Status:** verified for same-format callers only. Its conclusion that a native
  Responses target may keep `stream = true` is superseded by L018.
- **Evidence:** Switchyard `a13884c` routes and the retained built gateway were
  exercised on 2026-11-09. Unlike the documented Chat streaming-default issue,
  native Responses targets with `stream = true` preserved caller `stream = false`.
- **Verification:** `tests/test_responses_transport.py` covers six native aliases,
  both stream modes and default/caller effort overrides (24 subcases), preserving
  tool call/result IDs. All three route variants also pass built configuration
  validation. Agent/gateway Chat boundary fixtures pass for both Chat variants.
- **Action:** keep transport-specific regressions, and cover each inbound format
  against each upstream format: a same-format pass says nothing about a
  translated request (L018).
- **Limit:** synthetic provider acceptance does not prove real-provider support,
  full agent-to-native-Responses continuation, quality, latency or cost. Retained
  binary/source provenance was not rebuilt independently during this review.
- **Recheck:** provider adapter, merge/stream encoding, pinned gateway build,
  public aliases or route payload defaults change.

## L015: deploying current source requires build-to-workload image identity

- **Status:** verified source orchestration and synthetic public-entrypoint tests.
- **Evidence:** deployment alignment on 2026-11-09 based on agent `90fdaad4`,
  Switchyard `6088c2f`, context `4b9e7bf` and sandbox `ba97474`. Agent already
  built/published and deployed immutable references. Switchyard, context and
  sandbox v2 reused published images; sandbox v1 already built/pushed through its
  deployment script, but sandbox had no root Make target. All four now expose
  `make deploy` for current-checkout deployment while retaining durable assets.
- **Verification:** synthetic clients exercise public Make entrypoints, explicit
  settings/component selection, preflight/build/push failures and exact image
  references reaching Helm. Switchyard and sandbox deploy fresh digests; context
  passes unique versioned tags to selected owned components. Builds target the
  configured deployment architecture rather than assuming the host architecture.
  Chart checks retain existing PVC/resource wiring; no teardown path was added.
- **Action:** keep prebuilt/restart operations explicit, preserve saved provider
  selection, and verify newly published image identity at the workload boundary.
  Upstream images and external Hindsight retain their owners. Ordinary source
  review does not authorize running the deployment or publishing images.
- **Related regression:** sandbox's controller now launches the image recorded
  by the persisted run/session, not its newly deployed global default. Retain
  referenced registry digests while sessions can still run; deployment must not
  silently change their execution provenance. Pod-local v1 files remain ephemeral.
- **Limit:** no live registry publication, rollout, GPU/runtime execution or
  storage-recovery claim. Context's broader local build gate remains blocked
  by missing Docker CLI in the validation container; focused deployment and
  chart gates passed. Keep release names/namespaces/storage settings stable;
  storage migration is separate from redeployment.
- **Recheck:** image build mappings/platforms, Make/env precedence, rollout or
  recovery commands, PVC templates, session image identity or owner boundaries.

## L016: validation entrypoints must run on the maintainer's shell

- **Status:** verified source defect with offline regression on two shells.
- **Evidence:** Switchyard `bfb40e7`, reviewed 2026-11-09 on macOS where only
  bash 3.2 exists. `scripts/deploy.sh` and `scripts/render_routes.sh` used
  `declare -A`, `[[ -v ]]` and `mapfile`, so `make validate`, `make deploy` and
  the offline suite failed there: 19 failures and 4 errors, all shell-related.
  Context's root Makefile and operator scripts also require bash 4+ and
  `/usr/bin/bash`; its `scripts/tests` suite reports 5 failures and 5 errors on
  the same host before and after unrelated changes.
- **Verification:** ported both Switchyard scripts to prefixed scalars,
  `${!name+x}` and `while read` loops. The suite passes under bash 3.2 (70 run)
  and under Linux bash 5.2 in a container (142 run); remaining skips need the
  built gateway binary. Precedence tests for caller/.env/empty values still pass.
- **Action:** treat a failing shell-driven suite as a host-compatibility
  question before a routing defect. Keep deployment scripts within bash 3.2 or
  state the requirement; context remains Linux-operated by design.
- **Limit:** no live deployment was run; semantics were established by the
  synthetic command-peer tests, not a cluster rollout.
- **Recheck:** new shell scripts, Make `SHELL` settings or test harness changes.

## L017: templates and fallbacks must track the served information layer

- **Status:** verified source drift and fail-closed consumer; fixed with regressions.
- **Evidence:** agent `44b9370e`, context `3662469`, reviewed 2026-11-09.
  The agent `.env.template` named `llama-nemotron-embed-vl-1b-v2` and
  `llama-nemotron-rerank-1b-v2`; the retriever serves only the Nemotron 3.5
  models and the embedder has no legacy alias, so a template-built deployment
  loses every query embedding while readiness stays ready. The agent's upload
  metadata label `EMBEDDING_NIM_MODEL_NAME` defaulted to the old model and was
  generated nowhere. RSS discovery returned no sources on reranker failure
  although topology declares reranking fail-open. `refresh_promote.py` archived
  every `default` collection without a refresh fingerprint, including the
  agent's `meta` and `user_uploads*`.
- **Verification:** parent `test_context_boundary.py` now checks template and
  generated values against `rag-schema.yaml`; `contextctl` emits
  `EMBEDDING_NIM_MODEL_NAME` and both generated files pass `--check`; agent RSS
  tests cover fail-open discovery and fail-closed single-article mode
  (pre-existing test-order leak in that file: the full-file run fails after the
  first harness test in this environment, baseline included); url-ingest tests
  cover `refresh_owned` (48 pass).
- **Action:** compare operator templates with the generator, not only the
  generated files; apply the fail-open contract to every reranker consumer;
  scope destructive data migrations to owned collections.
- **Limit:** no live embedding, retrieval or promotion run; the Rust default
  for the metadata label is unchanged because no Rust toolchain was available.
- **Recheck:** served model IDs, generator keys, reranker consumers or shared
  Milvus database ownership change.

## L018: a target stream default breaks translated and stream-omitting callers

- **Status:** verified on the built agent and gateway; fixed with regressions.
  Supersedes L014's conclusion for native Responses targets.
- **Evidence:** 2026-11-10, agent `4da2bb16`, Switchyard `293eb62` built from its
  Dockerfile. A 72-case matrix (three provider files, shipped and toggled
  default, automatic and explicit route, Chat and Responses caller, stream false,
  omitted and true) showed one rule: a target `stream = true` survives only a
  same-format caller's explicit `false`. Every translated request and every
  caller that omits `stream` received SSE. `routes_openai.toml` shipped that
  default on all six targets, so the agent's non-streaming Chat forward for
  automation planning failed with 502 "invalid content type".
- **Verification:** the default is removed. `tests/test_provider_routes.py`
  forbids `stream` on every target offline (six targets failed before);
  `tests/test_stream_contract.py` calls every route of every provider file
  through both APIs in all three modes on the built gateway (21 cases failed
  before, none after). The boundary check's `autonomy_plan` case fails on the
  previous file and passes on the fix.
- **Action:** test payload defaults across the caller-format by provider-format
  matrix, and with the field omitted. Find the agent's non-streaming callers
  before judging a default harmless.
- **Limit:** synthetic providers only; the OpenAI variant was not deployed or
  sampled, and real provider streaming behavior is unverified.
- **Recheck:** gateway merge or translation patches, the pinned upstream build,
  provider payload defaults or new direct callers.

## L019: the gateway and the agent both retry, and the counts multiply

- **Status:** verified on the built joint boundary and in the patched gateway
  source. The retry owner is an open decision (Q002); no policy was changed.
- **Evidence:** same builds as L018. No provider file sets `max_retries` or
  `timeout_ms` on a client, so the gateway uses its defaults: two retries before
  a response (transport errors, timeouts, HTTP 408, 429 and 5xx; `Retry-After`
  honored up to 60 s) and no upstream deadline. Measured with synthetic 503s:
  one transient failure is absorbed by the gateway under the caller's ID and
  the agent sees success. A persistent failure costs 3 provider requests per
  agent attempt on an explicit alias and 6 on the automatic route, which then
  tries `default_target` as well, even when both targets name the same provider
  model. Measured at agent `max_retries` 1 and 2 (6 or 12, and 9 or 18,
  requests); by the same rule the shipped value of 3 gives 12 or 24 provider
  requests and 4 classifier calls for one logical model call.
- **Mid-stream:** the gateway never retries after a response starts. It ends the
  stream with a `SwitchyardError` frame whose message starts with
  `upstream transport error: ` (no `[DONE]`, no `response.completed`), for both
  caller formats. The agent retries only that envelope, as a new logical call.
  From source, not exercised: a mid-stream upstream deadline uses a different
  message that the agent does not retry, and needs a client `timeout_ms`.
- **Verification:** boundary cases `persistent_failure` (explicit and automatic,
  exact request counts from configured retries), `upstream_failure` and
  `midstream_abort`; Switchyard `tests/test_stream_contract.py` pins the frame.
- **Action:** count attempts per layer and per fallback target before tuning any
  one retry setting. Attribute a repeated wire ID to the gateway (corrects L006).
- **Limit:** synthetic failures; real provider 429 and `Retry-After` behavior,
  gateway cancellation on agent disconnect, and cost impact are unmeasured.
- **Recheck:** client `max_retries`/`timeout_ms`, the fallback patch, agent
  retry rules or the pinned upstream default.

## L020: direct model forwards carry the same correlation as model calls

- **Status:** verified source change, unit test and built joint boundary.
- **Evidence:** agent `model_endpoint.rs` forwards (the optional direct model
  endpoint and automation planning) sent no request ID, so their gateway spans
  could not be joined to the agent. They now send one opaque `dc-` ID per
  request in `x-request-id` and `x-switchyard-request-id` and log
  `model_forward_started`/`model_forward_responded` with an `origin`.
- **Verification:** a Rust test asserts one distinct ID per forward and that a
  caller-supplied `x-request-id` is not passed upstream; the boundary check
  finds the planning ID in exactly one agent event and in a gateway span.
- **Limit:** needs an agent rollout. The decision service still receives no
  correlation header (join through gateway events). Model calls that context's
  optional `devopsAgent` makes through Switchyard were not examined.
- **Recheck:** new direct callers of the model endpoint, the gateway metadata
  allowlist or forward logging.

## L021: build both binaries in containers when the host has no toolchain

- **Status:** verified on macOS arm64 with only Docker; closes the "no Rust, no
  gateway binary" gap recorded by earlier runs on this kind of host.
- **Evidence:** the Switchyard Dockerfile's `builder` stage and a Rust 1.95
  container produced Linux binaries that ran the boundary check and the full
  Switchyard suite in a container: 144 tests with 2 skipped, against 70 with 74
  skipped offline, and 21 boundary cases for each of the three provider files.
  This found L018 and L019, which the offline suites pass.
- **Action:** follow the container recipe in the contract map before reporting
  the built boundary as unavailable. Run the checks in an image whose libc is at
  least as new as both builds.
- **Limit:** a debug agent binary and a locally built gateway are not the
  published images; image-level checks such as the agent's `make runtime` and
  deployed digests remain separate evidence.
- **Recheck:** toolchain pins, the Dockerfile's stages or base images.

## L022: fixtures must use the owner's real response shape

- **Status:** verified source defect on both agent adapters; fixed with frozen
  parity cases. Not exercised against the built sandbox image.
- **Evidence:** sandbox `3f1cb92`, agent `4da2bb16`. A collected file cut by the
  collection budget is returned with its on-disk `size`, fewer bytes and
  `truncated: true`. The Rust and Python adapters required `size` to equal the
  decoded length, so they rejected the reply as invalid and never reached their
  own "truncated artifact" handling. The agent's truncation tests used a
  synthetic `size` equal to the content, a shape the service never returns.
- **Verification:** both adapters accept `size >= length` only when the file is
  marked truncated. The exporter freezes four such cases from the Python adapter
  into the shared fixture, which the Rust suite replays; every earlier frozen
  case is unchanged, and a Python test covers the publish path.
- **Action:** derive consumer fixtures from the owning service's code path, and
  check that failure handling is reachable with that shape.
- **Limit:** no run against Bubblewrap or a file larger than the real budget.
- **Recheck:** collection limits, per-file fields or adapter validation.

## L023: cite an ingested source by its identifier

- **Status:** verified source defect; fixed in the Rust runtime and the retained
  Python retriever with frozen parity cases. No live collection was read.
- **Evidence:** context `2f9bb87` writes each row's `source` as a JSON object
  carrying `source_id` and `source_name`, with `content_metadata.source_url`.
  The agent printed the first truthy of source, url or title, which for an
  object is its Python-style representation, so curated passages reached the
  model as `{'source_id': 'https://...', ...}` rather than a URL.
- **Verification:** object sources now resolve to `source_id`, then
  `source_name`, then `content_metadata.source_url`; strings, arrays and objects
  without an identifier keep their retained output. Six cases frozen from the
  Python retriever are replayed by the Rust suite.
- **Limit:** the refresh adds no title or ingest time to a row, and a `pdf://`
  identifier is not a URL the agent's http-only citation audit accepts. The
  other keys NV-Ingest places in `source` were not inspected.
- **Recheck:** refresh row schema, output fields or result formatting.

## L024: a dependency's timeout must fit inside the caller's deadline to fail open

- **Status:** verified source defect; fixed in the Rust runtime with a test.
  Extends L017's fail-open rule from errors to slowness.
- **Evidence:** the reranker client's 30 s timeouts equalled the 30 s search
  deadline that started earlier and wrapped embedding, search and reranking. A
  slow reranker therefore ended the whole retrieval with `TimeoutError` and
  discarded hits already found, although topology declares reranking fail-open.
- **Verification:** reranking is bounded by the caller's deadline less a margin
  and falls back to vector order; a delayed synthetic reranker returns unranked
  hits before the deadline, and a roomy or absent deadline still ranks.
- **Limit:** the fallback still waits almost the whole search budget; a shorter
  reranker budget is an owner decision. The retained Python retriever is
  unchanged, and no slow real reranker was exercised.
- **Recheck:** search or reranker timeouts, deadline nesting or new callers.

## L025: operator templates and documented examples are consumer inputs

- **Status:** verified source drift; fixed with offline parent regressions.
- **Evidence:** agent `4da2bb16`. `.env.template` left `UNIFI_MCP_SERVER` blank
  while the shipped workflow registers that group and the runtime rejects an
  empty MCP URL at startup; context generates the address. The same template
  suggested `daedalus/cheap`, an alias no provider file defines.
- **Verification:** `test_context_boundary.py` requires the generated address
  for every context-owned MCP server the workflow registers.
  `test_model_alias_boundary.py` requires every workflow default and every
  alias named in the templates, comments included, on every discovered provider
  file. Both fail on the previous template.
- **Action:** when a generator or provider inventory changes, check templates
  and commented examples, not only generated files and executable defaults.
- **Limit:** provider-specific extra aliases can exist; the test requires only
  that what the agent names is served everywhere. Deployed settings unverified.
- **Recheck:** new MCP groups, generator keys, provider files or template edits.

## Q002: open findings and decisions

From this run's read-only source reviews, with the cited settings re-read in
source; nothing here was exercised at runtime. Not fixed because each needs an
owner decision, a model or cluster, or a measurement. Decided earlier (user,
2026-11-09): provider affinity is Switchyard's `extra_headers`; a
deployment-wide `GLOBAL_SESSION_ID` is intended; the agent's unused
`x-switchyard-session-id` is a cleanup candidate, not a contract.

- **Model path.** Choose the retry owner and pin `max_retries`/`timeout_ms` per
  client (L019); with no upstream deadline the agent's 60 s idle timer is the
  only bound. Nothing probes the `decision-api` classifier before deployment,
  gateway readiness ignores it, and no repository defines that service: when it
  is unreachable every automatic call waits up to 2 s and runs at
  `default_target`. The selected provider file is not recorded on the workload.
- **Sandbox.** One execution per pod plus ClientIP affinity gives the single
  backend one slot; a busy 429 is returned to the model unretried although
  nothing ran. Up to 1 MiB of stdout/stderr enters model history uncapped. The
  tool description lists curl URL tests although the network is isolated,
  understates the `command` grammar and never mentions the 13 check/lint
  wrappers; the agent's tool-config rules require paired model behavior before
  changing it. Discovery prints the server maximum timeout, not the agent's
  60 s cap. Reserved environment names differ (agent 20 names and 2 prefixes,
  server 41 and 10) and are not advertised. An abandoned execution holds its
  slot until timeout. Exploration results are base64 and polled per model turn.
- **Context.** No working relevance floor: `distance_cutoff` assumes L2 and is a
  no-op on the COSINE curated collections, and the schema forbids negative
  thresholds although reranker scores are raw logits; needs calibration. The
  k8s MCP auto-approval list names 18 operations the default server never
  registers (latent), and `devopsAgent` advertises 300 to 900 s against the
  agent's 120 s group timeout. Calls to one MCP server run serially after a
  connect turn. Curated searches inherit Strong consistency (measure first). An
  empty reranker key falls back to `NVIDIA_API_KEY` as the bearer token.
- **Deployment.** The default agent chart has no egress to Switchyard, the v1
  sandbox or Hindsight (the site overlay adds them), and agent readiness does
  not check the model endpoint. Three owners hard-code the agent's namespace
  and release. Context topology changes do not reach the agent chart's policy
  values. Image prompt assistance is disabled when the gateway key is empty.
- **Next checks:** run the agent's image-level `make runtime` check on these
  changes; replay a curl request, a shell-syntax request and a lint request
  through the sandbox tool before editing its description; measure overlapping
  sandbox calls for 429s; read one live curated result for the `source` keys.
