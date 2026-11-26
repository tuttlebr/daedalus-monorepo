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
  automatic continuations reclassified at that revision. Rejected profiles never reach a provider.
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

- **Status:** historical behavior verified; the no-default remedy is superseded
  by the user's 2026-11-18 requirement that all generation calls stream. The new
  gateway policy forces SSE, including same-format explicit false, and both the
  runtime planning forward and its frontend consumer support it. Preserve the
  caller/consumer assessment lesson below; do not restore the old no-stream rule.
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

## L026: distinguish failed MCP execution from unknown effects

- **Status:** verified source defects and built-service regressions; production
  rollout and real-model wording are unverified.
- **Evidence:** 2026-11-15 UTC, agent baseline `484e308f` and context baseline
  `2f9bb871`. New Go regressions fail on the old source: `pods` resolves to the
  metrics API, command failures lack `isError`, and handler errors become RPC
  errors. The agent discards those RPC diagnostics as unconfirmed outcomes.
- **Fixes:** agent `c081e84d` and context `2113b673`.
- **Verification:** `resource_resolution_test.go`, handler/result tests,
  Rust/Python MCP tests, and the agent HTTP check in both preparation modes.
  `scripts/check_kubernetes_mcp_boundary.py` exercises the built agent and MCP
  binary against a local API/command fixture, including delayed deletion and
  partial command failure. The corrected path retains error evidence, never
  automatically replays calls, and verifies absence after deletion acceptance.
- **Action:** resolve unqualified Kubernetes resources deterministically across
  groups; preserve explicit group choice and reject unresolved ambiguity. Keep
  tool execution errors, RPC errors, and transport uncertainty distinct. An
  error may follow partial changes; successful submission is not completion.
- **Limit:** source corrections do not prove which API URL a historical live
  request used. Audit `status=ok` alone also cannot establish a subprocess exit
  code or the final resource state. New capture requires the context `.env`.
- **Recheck:** discovery/cache rules, SDK error representations, MCP envelopes,
  command execution, or mutation verification contracts change.

## L027: Responses snapshots must survive every accumulation boundary

- **Status:** verified synthetic regressions through built gateway/runtime,
  worker, Redis, WebSocket, browser rendering/reload and the official SDK.
  Deployment and live OpenAI behavior remain unverified.
- **Evidence:** 2026-11-15 UTC, agent baseline `c081e84d`, Switchyard initial
  baseline `5992752` and integrated upstream main `b88ea20`. Rig 0.43 streaming
  lost snapshot-only content after deltas. The pinned gateway upstream
  `336196f6` treated a snapshot correction as an upstream failure; its observers
  cut off the terminal event even after exact-replay handling was repaired.
- **Fixes:** agent `0c401cdf` and Switchyard `c4955d2`.
- **Action:** accumulate items/parts by their wire indexes. Treat done/terminal
  output as snapshots, including shortening and empty corrections. Preserve
  function call IDs and opaque reasoning for continuation, and validate final
  arguments before execution. Separate native snapshot projection conflicts
  from actual provider errors; append-only translated consumers must fail
  explicitly when they cannot represent a correction.
- **Consumer contract:** commit replacement text and a revision atomically in
  Redis; publish the revision with deltas and read it with status snapshots.
  Browser recovery must reject stale revisions and repair a missed replacement
  before applying offsets. UTF-8 Redis offsets and UTF-16 browser offsets differ.
  Roll out worker/frontend support before runtime replacement events.
- **Regressions:** agent `builder/runtime/tests/fixtures/responses-accumulation.json`,
  `frontend/e2e/tests/responses-accumulation.spec.ts`, worker/Redis/hook tests;
  gateway `patches/responses-native-snapshots.patch` and
  `tests/test_responses_transport.py`. Built tests must include the complete
  request path: codec tests alone did not reveal the observer truncation.
- **Scope/recheck:** text/refusal and function-tool accumulation, not UI support
  for every Responses media/hosted-tool type. Recheck on Rig/upstream changes,
  snapshot/terminal contracts, Redis persistence, worker revisions or browser
  reconciliation changes. Synthetic correctness does not establish quality,
  latency or cost on a live provider.

## L028: distinguish tool argument encoding from answer format

- **Status:** observed pre-execution schema rejection; verified compatibility
  recovery with synthetic requests against a built backend. Live recovery is
  unverified because historical argument contents were not logged.
- **Evidence:** 2026-11-15 UTC, agent baseline `0c401cdf`, Switchyard `c4955d2`.
  A daily-summary run rejected two renderer calls because `edition` was a string
  where an object was required, then selected sourced text fallback. Joined
  gateway correlation IDs and mounted configuration identify Baseten DeepSeek
  over Responses. HTTP success did not establish valid tool arguments. The
  evidence establishes the field type, not whether its contents were JSON.
- **Fix:** agent `8500085c`.
- **Action:** separate outer function-argument JSON, nested field types, and
  final answer format. In native preparation, decode a complete serialized
  object once only for a locally configured `briefing_renderer`, within its
  edition byte limit, then apply the unchanged schema and renderer gates.
  Keep call IDs and original model history; never repair prose, recursively
  decode, coerce unrelated tools, or skip source/HTML validation.
- **Regressions:** Rust catalog and agent tests cover single execution, aliases,
  size/type bounds, invalid nested fields and private-data exclusion.
  `builder/runtime_http_check.py` checks the advertised object schema, native
  and serialized editions through the real Python renderer, and bounded
  invalid-edition fallback. Its reasoning-progress fixture must include content
  indexes and distinct reasoning/message output indexes.
- **Limit/recheck:** direct Python inputs and Python preparation stay strict.
  The image check uses canonical local rendering recovery, not the production
  sandbox. Recheck tool schema ownership, preparation mode, edition byte limits,
  provider argument encoding, or renderer validation changes. Do not enable
  private body logging to diagnose a recurrence.

## L029: route composition and provider transport reach the optimization tools

- **Status:** verified parent-tool defect and repair; production policy unchanged.
- **Evidence:** 2026-11-16, parent `4d22b2e`, Switchyard `c4955d2`, agent
  `e144752`, context `2113b67`, sandbox `3f1cb92`. All five provider entrypoints
  use includes. The learner and alias regression parsed them as complete TOML;
  the learner suite failed before traffic. Its relay also accepted only Chat,
  and isolated gateway credentials were hard-coded to two providers.
- **Action:** compose selected files through the owner's renderer, snapshot and
  hash the composed source, fingerprint included fragments, discover credential
  variable names, and preserve each provider's Chat/Responses transport. Supply
  only dummy provider credentials to isolated gateways; never relay authorization.
- **Verification:** nested-include/snapshot, credential-stripping Responses relay,
  all-provider classifier-edit and built startup regressions; 21 built Baseten
  agent/gateway boundary cases; 156 Switchyard checks. A bounded live Baseten
  trial completed 16 requests through the real classifier and gateway, including
  tool continuation. Source/live parsed configuration matched; runtime hashes
  were stable. All five direct probes and all eight development answers passed.
- **Limit:** candidate routing passed 3/4 cases and was rejected before holdout.
  No quality, latency or cost improvement is established. Authenticated app
  traffic was not probed because its dedicated key file was unavailable; this
  is not evidence that the running agent needs a correlation rollout.
- **Recheck:** include composition, credential discovery, provider format,
  reasoning encoding, relay authentication or classifier/fixture contracts change.

## L030: the coding agent owns a broader optimization loop than a policy helper

- **Status:** explicit user correction and verified workflow limitation; no new
  application improvement is claimed.
- **Evidence:** on 2026-11-16 the user reviewed the co-design outcome as an audit
  rather than useful agentic optimization. Parent `2b6feaf` had a working scalar
  classifier tuner and authenticated literal-response probe, while Agent
  `e144752` already provided paired real-model/backend evaluations for tool
  behavior and research evidence recovery. The skill's outer loop named only
  classifier proposals and did not connect these broader candidate mechanisms.
- **Action:** let the coding agent select a task-level bottleneck, implement a
  causal code/configuration candidate in its owner, use the appropriate existing
  evaluator, retain/reject from outcomes and feed that result into the next
  experiment. Carry authorized candidates through rollout and the same acceptance
  checks. The classifier script keeps its existing narrow allowlist.
- **Limit:** passing smoke traffic, a route rubric or a token inventory is not
  an optimization result. The observed large input on a tiny task nominates a
  context-cost hypothesis; cached usage and payload composition must be measured
  before claiming waste or deleting capabilities. Review-only and deployment
  authorization boundaries are unchanged.
- **Recheck:** evaluator capabilities, ownership, candidate controls, runtime
  observability or explicit user optimization objectives change.

## L031: three layers serialized same-server MCP reads; overlap follows policy

- **Status:** verified on built agent images and the built context UniFi MCP
  server. Deployment and live behavior are unverified.
- **Evidence:** 2026-11-16, agent baseline `b9c9b48f`, context `2113b67`. Every
  MCP group had one scheduler slot (`Config::tool_concurrency`), dispatch held
  one session lock per user and group across the remote call, and the session's
  transport and raw-result capture took one request. Four reads to one server
  in one model response cost four call latencies; two runs of one user also
  queued behind each other.
- **Change (agent `840a0454`):** `function_groups.<group>.max_concurrency` (then
  1 to 8, default 1) lets tools whose policy is exactly `read_only` overlap,
  each on its own session. Every other operation and `__connect` stay exclusive
  and in proposed order within the group. A refused further session falls back
  to the first.
- **User direction:** on 2026-11-16 the user set the bound to 8 on every MCP
  group in the shipped workflow, replacing the first candidate's UniFi-only
  opt-in, then raised every limit to 16 (agent `7845a280`): the per-run cap,
  the accepted range and the unset fallback for MCP groups, webscrape and the
  source verifier, and every shipped value. A group or tool is now serial only
  when it states 1. An agent contract test requires the shipped values.
- **Verification:** `scripts/check_mcp_read_overlap.py`, frozen before the
  candidate, five alternating pairs at 400 ms synthetic latency: four reads
  1.79 s to 0.47 s (ratio 0.25 to 0.28 in every pair), six reads at bound four
  2.63 s to 0.85 s, two concurrent runs 3.52 s to 0.85 s. Groups without the
  opt-in, and an opted-in group whose tools are only auto-approved, stayed at
  one call in flight (ratio 1.00). A read, write, read, read batch kept the
  write alone and in order. Result digests, model rounds and call counts were
  identical across arms; a tool error, RPC error and timeout left siblings
  intact. `scripts/check_unifi_mcp_boundary.py` with the shipped group and the
  real server: four site reads 1.63 s to 0.43 s, controller peak four. At the
  shipped bound of 8 (three alternating pairs each): ten synthetic reads 4.42 s
  to 0.85 s with eight in flight, and eight UniFi site reads 3.28 s to 0.45 s
  with a controller peak of eight; every hard check still passed. At 16 on
  the `7845a280` build: sixteen synthetic reads 0.92 s at bound 8 to 0.54 s at
  bound 16, eighteen reads capped at sixteen in flight, a group that omits the
  key overlapping where the previous runtime ran it in turn, and sixteen UniFi
  site reads in 0.49 s with a controller peak of sixteen (five runs). The
  agent's built-image leaf check passes with unset scrape and verifier limits.
- **Action:** for a tool-phase latency hypothesis, find every serialization
  layer (scheduler limit, session lock, single-request transport, single-slot
  result capture) before proposing concurrency. Tie overlap to an explicit
  policy, not to the heuristic mutation detector, and keep order for the rest.
  Changing a fallback changes every configuration that omits the key: three
  tests and fixtures that checked queued calls relied on the old fallback of
  one and now state it. Size fixture peers for the concurrency under test: a
  Python `socketserver` backlog of five delayed one of sixteen simultaneous
  connections by a one-second retransmit, which looked like a slow call.
- **Limit:** scripted model and synthetic latency. No live server, rate limit,
  quota or session cap was exercised, and how often production responses batch
  same-server reads is unmeasured. Only the UniFi server was exercised with
  overlapping reads; the other enabled servers (Hue, ESPN, X, GitHub, Gmail,
  Calendar, Docs) were not, so lower a group's bound if its server throttles.
  The Kubernetes group has no `read_only` overrides, so it stays serial; adding
  them also changes charter verification (`verification_group_for`) and needs
  its own experiment. The Python MCP client ignores the bound. Sixteen
  concurrent source checks are sixteen concurrent model calls; their
  provider-side effect is unmeasured. Further MCP sessions use a separate pool
  of 512 connections; beyond it a read waits for the user's first session.
- **Recheck:** MCP SDK transport, session or lock design, approval-policy
  semantics, group opt-ins, or a server's session and burst limits change.

## L032: per-run ordering does not exclude other runs sharing MCP sessions

- **Status:** verified baseline defect; candidate retained locally; deployment unverified.
- **Evidence:** 2026-11-17, agent `7845a280`, parent `1d791d58`, Context
  `2113b673`, Switchyard `c4955d22`, sandbox `3f1cb927`. The per-run scheduler
  ordered siblings, but an exclusive MCP call locked only session zero. A read
  in another run could use another session during that call, or an exclusive
  call could start when session zero freed while another read remained active.
  Built baseline fixtures reproduced inconsistent snapshots in both directions.
  The fresh bounded runtime capture contained no agent tasks; this does not
  establish that a production request encountered the race.
- **Change:** the agent's MCP dispatcher uses one fair semaphore per user and
  group within a process. A policy-marked read takes one permit; other calls
  take all permits. Admission precedes session acquisition, stays outside initial
  OAuth consent, and refreshes credentials after waiting. Weak entries expire
  when callers leave; cancellation releases queued admission without replay.
- **Verification:** built agent with scripted model/MCP peers checks both race
  directions, independent users/groups, retained read overlap, cancellation and
  exact call/result binding. Rust regressions additionally hold a queued writer
  and prove later reads wait, check weak-entry reclamation, and retain refused
  session fallback. Full Rust and both preparation-mode built HTTP checks pass.
  Three alternating pairs reduced conflicts from 6 to 0 and consistent reads
  improved from 24/30 to 30/30, with unchanged calls/rounds and existing result
  digests. Sixteen-read median tool phase was 574.5 versus 579.0 ms; read overlap
  stayed at sixteen. This establishes a correctness gain, not a speedup. See the
  private experiment ledger for evaluator, image identities and limitations.
- **Action:** review exclusion at every scope that shares a resource: a batch,
  concurrent runs, a process and replicas. Test mixed calls from independent runs;
  separate read-only and write-only batches cannot establish mixed exclusion.
- **Limit:** process-local admission does not coordinate replicas or separate
  groups targeting the same service. A canceled or timed-out remote request may
  continue executing; this change retains existing uncertain-outcome semantics.
  No wire/configuration, approval policy or endpoint changes are required. Older
  images remain compatible but lack the new exclusion. Real-model behavior,
  live server effects and production performance are unmeasured.
- **Recheck:** shared MCP manager lifetime, approval policy, session selection,
  semaphore bounds/fairness, token refresh or cancellation/reset semantics change.

## L033: dispatch can validate metadata without projecting every tool schema

- **Status:** verified built experiment; no-cache candidate retained locally;
  deployment unverified.
- **Evidence:** 2026-11-17, agent `7845a280` plus retained L032 admission fix,
  parent `1d791d58`, Context `2113b673`, Switchyard `c4955d22`, sandbox
  `3f1cb927`. Every MCP dispatch constructed the full exposed JSON schema
  catalog before selecting one tool. Warm synthetic tasks scaled with catalog
  size despite no further tools/list requests. Compiled validators were already
  cached, so validator compilation was not the proposed cause.
- **Change:** separate filtering and full-catalog description validation from
  JSON projection. Dispatch borrows the selected original Tool; discovery and
  `__connect` still project identical schemas. Add no cache or freshness rule.
  A missing description on any exposed sibling must still reject a call;
  checking only the requested tool would silently change existing behavior.
- **Verification:** three alternating image pairs at 16/64/256 tools and a
  512-tool size holdout, twelve warm tasks plus one cold task per arm/size.
  All 312 tasks retained identical schema/result hashes, sixteen calls and two
  model rounds. At 64 tools, median warm CPU per task fell 30.0 to 17.5 ms;
  tool-phase CPU 23.3 to 10.0 ms; completion 30.0 to 19.15 ms. At 16 tools,
  total CPU fell 14.2 to 10.8 ms. The 256/512 stress sizes also passed. Cold
  64-tool CPU stayed 210 ms. Full Rust, both preparation-mode built HTTP,
  schema-error/filter/reconnect, overlap and prior exclusion checks passed.
- **Action:** avoid constructing public schema JSON for internal membership
  checks. Preserve whole-catalog validation, filter precedence, exact override
  lookup, input/output validation and ordering. First remove unnecessary work;
  a schema cache would add retention/invalidation costs this result does not need.
- **Limit:** synthetic approximately 1 KB nested schemas, scripted model, local
  peers and 10 ms CPU ticks aggregated across tasks. Phase CPU includes other
  runtime work; total CPU corroborates the causal paired change. Source include
  counts are 2–49 except unbounded Hue; 256/512 are stress cases, not a live
  inventory. Real catalog shapes, model behavior, production latency and billing
  remain unmeasured. No context-size or token saving is claimed. Runtime capture
  contained no agent tasks; it does not establish live impact.
- **Recheck:** exposure/description policy, schema shape, tool selection,
  connect/discovery, input/output validation or reconnect behavior changes.

## L034: a failed chat can preserve activity and still have no final answer

- **Status:** observed live and verified with a built frontend. Production
  rollout of the fix remains unverified.
- **Evidence:** on 2026-11-20, an exact-ID join in `daedalus` linked two
  model HTTP 429s and a third request that opened an HTTP 200 Responses stream
  before failing with a non-retryable `model_stream/response` error. The final
  attempt emitted zero assistant bytes. The failed job and the saved assistant
  message contained 98 bytes from an earlier model round and 52 activity
  entries. The final failure code is unknown.
- **Action:** compare the last model call's output counters, the worker's
  terminal job status and the owned conversation before diagnosing data loss.
  Check the browser both immediately and after reload. The interruption banner
  uses the presence of saved assistant text to describe what the user can see.
  Tool activity remains available through the existing disclosure.
- **Verification:** the incumbent browser showed the preserved text and the
  misleading banner. The candidate passed the same terminal-error fixture with
  and without saved text and the success/EOF formatting holdouts. No wire or
  persisted-error changes are required. The deployed incident's browser state
  and candidate rollout remain unverified.
- **Recheck:** stream error wording, error finalization, activity display, and
  the chat status or conversation recovery path.

## L035: source verification must request SSE and verify its terminal state

- **Status:** observed live and reproduced through the built gateway and
  pinned client. Production rollout of the fix remains unverified.
- **Evidence:** on 2026-11-20, the Python source verifier reported
  `AttributeError` during a failed chat. Both the deployed backend and built
  Switchyard artifacts reproduced the same error with a synthetic Responses
  provider. Switchyard returned configured SSE to a verifier that requested a
  unary result. Streaming alone let the pinned LangChain client return text
  from failed and truncated Responses streams in the direct fixture.
- **Action:** request streaming explicitly in the verifier and require
  Responses `status=completed` or Chat `finish_reason=stop` before accepting
  critic text. Preserve claim-verdict schema validation. Check leaf model
  clients separately when changing the transport used by the main agent.
- **Verification:** through the built gateway, the two complete Chat/Responses
  cases went from zero correct verdict texts to two. The four failed or
  truncated cases stayed rejected. The capture does not establish the source
  verifier failures as the cause of the final main-model stream error.
- **Recheck:** LangChain/OpenAI dependency upgrades, the verifier's model
  client, and Switchyard required-streaming or terminal-event handling.

## L036 — KV reuse across effort changes on Baseten

On 2026-11-20, eight bounded Responses requests exercised the mounted
Baseten profile for DeepSeek V4.1 Flash 1017 Fast. Two independent synthetic
prefixes tested high/high/low/low and the reverse order. All eight returned
the exact requested answer. Every same-effort repeat reported 5,120 cached
input tokens out of 5,260. Both effort switches reported zero. Run-level usage
from two ordinary tasks in the same window included substantial reuse. Their
per-round attribution was unavailable.

A 16-request direct Baseten control repeated both orders with the configured
session affinity header present and omitted. All four switches reported zero
cached tokens, and all eight same-effort repeats reported 5,120. The model's
reference encoder and tokenizer agreed for only the first eight tokens between
low and high; the ninth encoded 50 or 75 before the system instructions.
Replica identity and the hosted renderer were unobserved. Preserve affinity
for placement of related requests. Recheck the rendering after model changes.
[Baseten cache measurements](https://docs.baseten.co/inference/model-apis/pricing-and-limits#check-cache-reuse)
and [pinned model encoder](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/08c8657f02291e11b6f6b63e0e16014f8e748518/encoding/encoding.py).

In a subsequent 12-request hosted comparison, retaining a previously served
high target for two low-classified tool continuations recovered 5,376 cached
tokens on each continuation. Both policies returned the exact answers and ran
each tool once. Across the affected tasks, uncached input fell from 22,072 to
11,334 tokens. Output grew from 202 to 244 tokens and both continuations took
longer. A harder low-to-high holdout kept its escalation. The classifier was
scripted and the sample has one pair per task. Keep the mechanism opt-in and
preserve explicit effort. Recheck after provider, model or template changes.
Test longer chains with the real classifier before changing the default.
Preserve the accepted low target as a fallback when retained high fails before
streaming. After visible output, surface a failure with the partial result.

Eight direct Baseten Responses calls on GLM-5.3-Fast tested both switch directions
with one configured affinity value. The low/low/high/high sequence reported
0, 5,376, 0 and 5,376 cached tokens out of 5,391. The high/high/low/low
sequence reported four zeros, including both same-effort controls. Only the
low-to-high switch was bracketed by warm controls. The GLM-5.3 reference
template and tokenizer diverged at token nine before tools or messages. Verify
each direction with warm controls before transferring an effort-retention policy
between models. [Z.ai reference template](https://huggingface.co/zai-org/GLM-5.3/blob/ba32f8c19c8738e2c57c71798c601d477a7bf844/chat_template.jinja#L3)

The user selected one automatic choice per Daedalus run on 2026-11-20 for
every provider profile. Account for expected synthesis and verification when
classifying the initial task. Keep effort through tools, retries, active-run
steering and final synthesis. A new run in the same conversation gets a fresh
choice. The explicit profile and provider fallback contracts still apply.
In 98 paired local tasks across seven route sources and two API formats, the
run-scoped implementation made 70 classifier calls versus 154, with the same
210 answering requests and 112 tool calls. This supersedes the earlier
Baseten-specific opt-in recommendation. Recheck model accuracy and cache
savings using hosted task outcomes after rollout.

## L037 — Validate provisional work at each completion boundary

On 2026-11-20, local fixtures against agent 9b655e6a and Switchyard 32729d9
reproduced partial-result failures. A Responses provider's
bare SSE sentinel after valid-looking tool arguments allowed the incumbent
gateway and agent to execute a tool. Require the typed terminal event and
exercise the built consumer with a tool execution counter. On Chat streams,
check the finish reason for the choice that supplied the tool fragments. Retain
text-only sentinel handling and compatible explicit stop conventions.

A deferred catalog that ended in a conflict could acknowledge discovery and
abort sibling calls. Validate the full addition before acknowledging discovery,
then check the failing call, the surviving catalog and each sibling receipt
through the next model request.

A live stream reader retained an ordered copy of tool activity even after the
Redis steps key disappeared. Finalizing from that copy preserved the evidence
in terminal status and in the saved conversation after reload. On process
death the worker depends on the durable checkpoint. When job status expires, a
transient failure to read the saved conversation can hide a completed receipt.
Retry the owned history read and restore the saved outcome. In a Chromium
fixture, this recovered the turn after one HTTP 503 with zero new submissions
or conversation writes. Recheck these paths when changing stream failure
handling, lease handoff, history recovery or persisted state formats.

## L038 — Required report submission needs its own correction budget

An autonomous run on November 26, 2026 ended after two different validation
errors disabled its only publication tool. All 43 model calls finished. The
worker saved an uncertain interruption. A separate chat completed and its saved
reply matched the job result. Check the automation record and chat job
independently when tracing a report of lost streams.

With agent `d99660ca` as the source baseline, the incident image failed a
synthetic summary-then-evidence repair after a bounded series of reads. The
local candidate recovered the report using only the submission tool. A repeat
failure after a write retained the attempted-mutation flag and the fixture
service received the write once. An interactive chat held open across report
failure received its full reply. Recheck the built charter fixture when changing
tool disabling, completion budgets, Pydantic validation or worker error handling.

## L039 — Recover tool evidence when the model rejects a continuation for length

On November 26, 2026, an agent run at `fbc69106` completed 23 tool calls before
the model rejected a 281,343-token continuation against its 262,144-token window.
Switchyard returned HTTP 200 and carried the validation error in SSE. Join the
backend model-call ID to the serving frontend's request and inspect the terminal
error. Cached tokens still occupy the model's context window.

Agent `160e3220` archived eligible completed tool results in the existing
user-scoped output store before retrying. A live application probe through a
non-node LAN client exceeded a later 524,288-token window with 966,271 input
tokens. The retry used 56,790 tokens, recovered the exact checkpoint and
finished with one sandbox execution and one lookup. Exercise archive failure,
retriever availability, receipt identity and remaining retry budget when
changing this path. The built [research check](../../../../submodules/daedalus-agent/builder/migration/research_check.py)
covers both preparation modes.

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
  connect turn unless their tool is policy-marked `read_only` (L031; the bound
  is 16 unless the group states less). Kubernetes reads are not marked
  `read_only`, so they stay serial. Curated searches inherit Strong consistency (measure first). An
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
