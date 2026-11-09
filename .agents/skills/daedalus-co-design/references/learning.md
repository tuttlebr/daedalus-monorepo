# Verified lessons and open questions

Keep current reusable knowledge, not a run transcript. Follow
[the evidence workflow](runtime-evidence.md) when revising entries.

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

- **Status:** verified source inconsistency; live impact unverified.
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
  pairs. SDK transport retries retain the logical call ID. Agent-level retries
  and continuations get new IDs. Count repeated upstream attempts separately;
  never infer a new agent call merely from another upstream request.
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
