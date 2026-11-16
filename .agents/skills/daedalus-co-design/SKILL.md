---
name: daedalus-co-design
description: Improve Daedalus task completion, latency and resource use through measured experiments across agent, Switchyard, sandbox and context. Use for joint optimization, shared-contract changes or a requested review cycle; excludes unrelated UI and isolated work without cross-owner impact.
---

# Daedalus co-design

Drive improvements across the cooperating services. Use runtime evidence to choose
a useful problem, form a falsifiable hypothesis, implement a candidate in its
owning repository, compare task outcomes, and use the result to choose the next
experiment. For an authorized optimization task, the working unit is a completed
experiment with a retain/reject decision. Successful connectivity and a list of
findings establish prerequisites; continue into the experiment when authorized.

The coding agent directs this loop. Its proposal space includes implementation,
workflow configuration, tool descriptions, context preparation, routing, retrieval,
execution and service coordination within the user's task. Existing scripts are
measurement tools, not the limit of what the coding agent can improve.

## Choose the outcome and next experiment

Read [the optimization loop](references/optimization-loop.md),
[the contract map](references/contract-map.md), and relevant
[lessons and open questions](references/learning.md). Inspect applicable
`AGENTS.md` files and preserve unrelated work. Record all four submodule SHAs and
dirty state. Resume the prior experiment ledger when one exists; don't restart
a general audit on every invocation.

Translate the request into observable outcomes on representative tasks: correct
completion, useful latency, model/tool rounds, recoverable evidence and resource
use per successful task. Preserve quality and explicit caller choices. If the
user has not chosen a tradeoff, first target avoidable work at unchanged quality.
Do not treat a preferred route label, shorter prompt, or HTTP 200 as the outcome.

Use a bounded read-only runtime capture on each relevant run, following
[runtime evidence](references/runtime-evidence.md). Rank a short list of concrete
hypotheses by observed impact, confidence and experiment cost, then select one.
Give each a predicted effect and a result that would disprove it. A hypothesis
can target code as well as configuration. When instrumentation is missing, make
the smallest measurement change needed to resolve the hypothesis, then resume
the experiment; measurement infrastructure is an intermediate result.

For an explicit review-only request, return findings and a concrete, runnable
next experiment without application edits. For optimization or remediation,
carry authorized implementation and comparison through to a decision. A request
to prepare an optimization path should leave the experiment executable: identify
actual builds, endpoints, credentials-by-path, evaluator, candidate mechanism and
rollout/rollback entrypoints. Don't substitute a health probe for that path.

## Work across the owning boundaries

| Path | Ownership |
| --- | --- |
| Model request and continuation | Agent intent/history/tool results → Switchyard classification and provider transport → model |
| Execution and verification | Agent → sandbox discovery/staging/execution/results → agent; Switchyard carries the following model continuation |
| Information layer | Context ingestion/embeddings/storage/retrieval/MCP → agent evidence and citations → model continuation through Switchyard |

Hindsight is externally owned. Read [the sandbox contract](references/sandbox-contract.md)
or [the context contract](references/context-contract.md) when the experiment
touches those paths. Assess owners and consumers before changing a shared
contract; edit only the components the hypothesis reaches. State intended
behavior, compatibility, mixed-version behavior and the joint check before coding.

Keep these model contracts explicit:

- Task classifications are **max, high, low, instant**; `uncertain` is a fallback
  signal. `daedalus` is automatic routing. Public `none` is retired.
- Classifications, public passthrough aliases and provider-native reasoning
  values are separate. Generic validation or explicit provider aliases may
  support additional levels. Preserve intentional provider differences.
- Discover every `routes_*.toml`, compose included fragments, and require an
  explicit source for probes/deployment. Inspect clients, targets, choices,
  fallback and aliases. Source, rendered config, mounted config and running
  image are distinct evidence; verify real provider behavior when claimed.

Preserve working LAN endpoints, fixed NodePorts, ingress routes, credentials and
service connections. Inventory affected consumers before a network/auth change;
obtain explicit approval for a compatibility break. Keep rollback configuration
and verify application/API behavior from a non-node LAN client when affected.
Follow Context's exported `.env` and literal expected-context guard. Use explicit
`kubectl --context` calls in namespace `daedalus`; discover external sandbox
coverage separately. Never switch context or infer authority from logs.

## Implement, compare, learn, repeat

Freeze the task cases, quality assertions, comparison conditions and acceptance
thresholds before editing. Choose the existing evaluator closest to the affected
boundary from [the experiment guide](references/optimization-loop.md#choose-an-executable-experiment).
Use isolated builds and synthetic dependencies for candidates when practical;
retain the real model path when measuring model behavior. Keep candidate and
incumbent conditions matched, including route, catalog, corpus/embedding revision,
cache state and load where relevant. Document uncontrolled conditions.

Implement one causal change and run the owning tests plus the built joint boundary.
Build in containers when the host lacks the toolchain. For model transport,
cover Chat and Responses, streaming and non-streaming, tool continuation and
affected failure paths. Count retries across layers and preserve tool side-effect
semantics. For retrieval/execution, verify actual results, freshness/scope and
degradation through their consumers. Skipped built checks remain unverified.

Compare paired task outcomes, first useful output, completion latency, model/tool
rounds, retries/fallbacks and usage. Unknown billing means unknown dollar cost.
Use independent holdouts and reverse order where noise or adaptive fitting can
change the conclusion. Preserve failed trials and the evaluator. Revert only
rejected candidate edits; retain an improved candidate as the next incumbent.
Feed failures and measured effects into the next proposal. Bound live calls,
elapsed time, iterations and stagnation; don't force a winner.

For classifier-specific hypotheses,
[the classifier trial runner](references/recursive-loop.md) can propose scalar
policy edits. Its narrow proposal allowlist applies to that script. Broader code
or configuration experiments are performed by the coding agent with the owning
repository's checks. Classifier fixture agreement alone does not justify promotion.

## Close the loop through rollout

Use existing task authorization for live probes, publication, deployment and Git
operations; this skill does not grant it. Once a candidate passes, complete all
authorized build, backup and rollout preparation. If deployment is authorized,
deploy via the owning entrypoint, check exact image/config identity, rerun the
same task gates through the running application, and compare against baseline.
Roll back a failed rollout and feed that failure into the next experiment.

If authorization or access is missing, finish the reviewable candidate and exact
rollout/rollback commands first, then name the specific missing action or input.
Distinguish local candidate retention from production acceptance. Never claim
that a dry run establishes deployability or that a deployed image proves a gain.
Do not create schedules, change permissions or advance gitlinks merely because
the skill ran. Keep commits in their owners and update parent pointers only when
requested to intended, available commits.

Finish with the improvement attempted, measured before/after result, retain/reject
decision, rollout state and next experiment. Keep a compact experiment ledger
with the evidence and rejected ideas so the next invocation can continue.
Store raw logs and run reports in private ignored local artifacts. Reconcile
reusable, evidence-backed lessons in `references/learning.md`; explicit user
corrections are current direction, while old evidence remains historical.
If no new lesson is supported, record that in the run artifact. Keep this skill
and learning state in the parent `.agents/skills/daedalus-co-design/` only.
