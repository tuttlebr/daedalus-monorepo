# Agent-directed optimization

The coding agent owns experiment selection, implementation and iteration across
the four repositories. The classifier runner is one specialized tool. Use
the existing application evaluators, builds and deployment entrypoints for other
changes; don't build another general optimization framework before using them.

## Carry state between experiments

Keep a compact ledger under the ignored parent `.artifacts/daedalus-co-design/`.
Record the objective, incumbent commits/configs/images, candidate diff, task-suite
identity, evidence paths, verdict and next action. Include rejected hypotheses
and why they failed. Resume this ledger on later invocations; verify the running
incumbent before reusing a baseline. Never silently inherit an old candidate or
compare measurements across changed services.

Choose the next experiment from evidence, including unsuccessful trials. A useful
entry has enough information for another coding agent to act:

| Field | Required content |
| --- | --- |
| Hypothesis | Suspected cause, predicted task-level effect and contrary result |
| Scope | Owning files and consumers; one causal change |
| Baseline | Build/config identity and representative task measurements |
| Candidate | Exact patch or overlay and how it is exercised |
| Evaluator | Frozen success assertions, repeated pairs and independent regressions |
| Budget | Calls, wall time and stop conditions proportional to the experiment |
| Verdict | Retain, reject or unresolved, with measured evidence |
| Continuation | Next discriminating experiment or authorized rollout action |

Prioritize observed avoidable work and failed tasks over speculative tuning.
Large token counts, latency and errors nominate a hypothesis; attribute their
cause before changing behavior. Total input can include instructions, schemas,
history, retrieved evidence, memory and repeated tool results. Cached input is
different from uncached input. Measure contributions using synthetic requests
or content-free counters; don't enable private prompt/body logging.

## Choose an executable experiment

Paths marked Agent or Switchyard are relative to that submodule. Parent script
names refer to this skill's `scripts/`. Inspect current CLI options and owning
instructions before invocation. Run from the owning repository when its tool
imports depend on that working directory.

| Hypothesis | Candidate mechanism | Existing experiment and quality gate |
| --- | --- | --- |
| Instructions or runtime behavior cause wrong tools, extra model turns or repeated failures | Same backend image with allowed workflow overlays, or baseline/candidate images for code changes | Agent `evaluation/tool-correctness/run.py`: actual Rust loop, real model, native clock/skills and isolated read-only MCP; checks choices, arguments, result IDs, dependency order, error handling and exact answers |
| Large tool evidence repeatedly consumes context | Compaction/recovery or research-output candidate in an isolated backend | Agent `builder/migration/research_check.py` and `research_workflow_check.py`: recover omitted evidence, exact Unicode facts, citations and continued tasks without duplicate fetches; compare recurring input and task latency |
| Model routing or provider translation causes wasted work or failed continuations | Selected route policy or gateway/agent code candidate | Parent `check_effort_boundary.py` and Switchyard built transport suites, then representative agent tasks with real models; use `co_design_loop.py` only when classifier tuning is the hypothesis |
| Sandbox setup, discovery, execution or result handling dominates | Agent adapter or sandbox implementation candidate | Passing/failing synthetic execution through the built agent and sandbox, including timeout, workspace isolation and required artifact publication; see `sandbox-contract.md` |
| Retrieval latency, ranking or evidence quality limits completion | Owning retriever/agent code or selected retrieval configuration | Frozen synthetic corpus/query through the built consumer, with relevant/correct passages, citations, authorization, missing-data and failure behavior; see `context-contract.md` |
| Tool scheduling makes the tool phase cost the sum of independent calls | Agent scheduler or MCP session candidate image, or a group's `max_concurrency` opt-in | Parent `check_mcp_read_overlap.py` in each arm's image, alternating order, plus the affected real server (`check_unifi_mcp_boundary.py`); identical results, rounds and call counts, exclusive ordered writes |

The tool-correctness harness already offers 25 workflow cases, synthetic catalog
distractors, alternating arm order, multiple repetitions and route/config hashes.
Use its documented workflow overlays for supported fields; do not expand an
evaluator's allowlist just to admit a candidate. A different implementation
belongs in a candidate image with the same evaluator. Tool-description changes
need an appropriate catalog fixture because workflow overlays cannot replace
the actual function schemas/descriptions.

The application compatibility API is a running-system acceptance surface. It
executes server-side tools, but the external response does not expose all internal
tool traces. Use observed run/correlation IDs for trace validation. A caller's
output-token limit does not bound internal model work. Keep app probes focused
and bounded; use isolated backend fixtures for mutating or lengthy workflows.

## Start with a matched baseline

For model behavior, use real models and controlled synthetic data. For dependency
or fault behavior, use deterministic peers until the candidate passes. Include
the motivating task, a distinct task that could regress and a failure/recovery
case. When optimizing a broad surface, use the full relevant suite and fresh
heldout tasks rather than selecting only easy cases.

In the agent repository, the existing paired harness can compare one immutable
image with two allowed workflow overlays, or two immutable images for code:

```bash
builder/.venv/bin/python evaluation/tool-correctness/run.py \
  --baseline-image "$BASELINE_IMAGE" \
  --candidate-image "$CANDIDATE_IMAGE" \
  --baseline-source-revision "$BASELINE_REVISION" \
  --candidate-source-revision "$CANDIDATE_REVISION" \
  --baseline-overlay "$BASELINE_OVERLAY" \
  --candidate-overlay "$CANDIDATE_OVERLAY" \
  --base-url "$SELECTED_GATEWAY_URL" --model daedalus \
  --route-configmap "$EXPECTED_CONTEXT" daedalus switchyard \
  --suite workflow --catalog-size 64 --repetitions 3 \
  --output "$FRESH_EVIDENCE_DIRECTORY"
```

These variables are explicit experiment inputs, not defaults. Supply the gateway
credential by the harness's documented `TOOL_EVAL_API_KEY` environment interface;
the Daedalus application key is only for the application endpoint. A gateway
that needs no authentication can use a synthetic placeholder. Do not send an
application credential to the gateway. Export Context's environment/context guard
before a ConfigMap read. See the owning
[harness guide](../../../../submodules/daedalus-agent/evaluation/tool-correctness/README.md)
for request limits, container networking, source identities and output semantics.

The paired harness's request count is backend task attempts, not internal model
calls. Its workflow iteration limit and timeout bound each attempt, but do not
provide an aggregate model-call ceiling. When a user sets a model-call budget,
enforce it at the model transport or use an evaluator with that bound before
starting. Do not present a backend request limit as an equivalent token/cost or
model-call limit. The classifier runner separately counts its own issued calls;
provider and internal agent retries still need accounting.

For a small discovery budget, freeze a narrow case set and reserve calls for
independent holdouts before starting. This harness currently has no case-selection
flag; use a focused fixture or add a bounded selection mode to the existing
evaluator when authorized. Count outbound attempts, including retries and
classification calls when the budget covers them, at the boundary that issues
them. Reserve capacity before concurrent sends so in-flight requests cannot
overshoot the ceiling. Stop on exhaustion and report an incomplete comparison;
budget exhaustion cannot turn partial evidence into acceptance.

For an instructions-only candidate, use the actual incumbent instructions in the
baseline overlay; the harness's short synthetic default is not a production
baseline. This fixture uses a synthetic catalog and disabled memory. Its results
do not establish production full-catalog or personal-memory performance.
Before a broad efficiency claim, test the actual affected catalog and running
application, and record any coverage gap.

An A/A comparison can estimate noise or verify the harness, but it is not an
optimization result. Don't repeatedly measure A/A while a supported candidate
is available. A reduced discovery pass can guide experiment selection; label it
as such and keep it separate from promotion evidence.

## Make the candidate earn retention

Choose a practical effect threshold before collecting candidate results. Preserve
all previously successful task behavior and hard compatibility/safety contracts.
Measure success per case as well as aggregates; failures remain in denominators.
Require the claimed benefit to survive paired ordering/repetition and the
relevant independent holdouts. A gain can be improved correct completion,
less repeated work, lower latency at retained quality, or lower measured resource
use at retained quality. Route-label agreement alone is diagnostic evidence.

If a cheaper/faster candidate degrades quality, keep the incumbent unless the
user explicitly accepts that measured tradeoff. If a result is inconclusive,
run the smallest discriminating experiment instead of rewriting policy to chase
noise. Reject a failed candidate, retain its evidence and use the failure to
revise the causal hypothesis. Change the evaluator only for an independently
demonstrated evaluator defect, version it, and restart the affected baseline.

Treat measurement work as a phase with a specific exit condition. For example,
attribute serialized input by instructions/catalog/history/results, then test
one candidate that removes redundant transmission while preserving access to
every capability. A token inventory alone does not complete that optimization.
Don't lower history/output limits or remove tools merely to make input smaller.

## Promote and verify the same outcome

Use [deployment ownership](contract-map.md#deployment-entrypoint-contract) and
the current owner's instructions. Prepare an exact candidate build/config,
release/component selection, baseline backup and rollback path. Preserve existing
site overrides and immutable image references; resolve source/runtime drift
before rollout. For shared contracts, document rollout order and mixed versions.

When deployment is authorized, use the owning entrypoint and rerun the same
quality gates against running services. Verify application/API behavior and
non-node LAN consumers where affected, then compare the claimed metric under
matched conditions. Successful Helm reconciliation only completes the control
plane step. A regression requires rollback and another experiment, not relabeling
the local candidate as a production win.

Without deployment authorization, leave the tested patch/images and concrete
commands ready for the final approval step. Do not repeatedly ask for authority
already granted. Without a needed key, environment, build or evaluator, finish
independent work and identify the precise missing prerequisite. Never manufacture
access or widen permissions as an optimization.

End each cycle with an experiment decision and the next action. Keep reusable
lessons concise and evidence-backed in `learning.md`; keep raw trials, site data
and full patches/reports in private ignored artifacts. No scheduled or unattended
optimizer is installed by this skill.
