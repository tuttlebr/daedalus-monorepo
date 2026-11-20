# KV-cache investigation and remediation

Find the architectural decision that makes useful prompt state harder to reuse.
Compare requests within one provider, model revision, API and cache scope first.
Use the [contract map](contract-map.md) to trace the affected model path. Include
context or sandbox only when their output or metadata contributes to the change.

## Trace what breaks reuse

- Inspect the agent's instructions, tool definitions and order, history replay,
  retrieval or memory placement, tool results, compaction and retry guidance.
  Look for avoidable early variation such as timestamps, request IDs, changing
  catalog order or rewrites of prior turns. Identify which changes convey fresh
  information or enforce authorization and must be preserved.
- Follow Switchyard's effective route, upstream request translation and provider
  rendering. Check where model, API format, reasoning effort, tool schemas and
  history change. Automatic routing can change targets or effort after a tool
  result or on fallback. A single model can still get different prefixes when
  the provider renders effort near the beginning. For example, DeepSeek 1017's
  reference encoder puts effort before system instructions. Verify how the
  selected hosted endpoint behaves with the actual payload.
  [DeepSeek reference encoder](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017/blob/main/encoding/README.md#thinking-mode)
- Check cache placement separately. Distinguish configured provider affinity,
  correlation IDs, tenant scope and the provider's cache key. Confirm the model
  and backend pool when visible, and account for minimum cacheable length,
  block size, expiration, eviction and load where relevant. Assume a new provider
  starts cold unless shared cache behavior is established.
- Compare synthetic requests at both wire boundaries and locate the first
  difference in the rendered token prefix when the tokenizer and template are
  available. Use provider cache metrics or reported usage to establish hits on
  hosted endpoints. Follow [runtime evidence](runtime-evidence.md) and use
  content-free counters for live work. Keep prompts, histories, schemas,
  credentials and affinity values out of persistent logs and tracked artifacts.

## Test one cause at a time

Start with a fresh synthetic prefix of known cacheable length, then repeat it
under the same provider, model, effort, catalog and affinity to establish a warm
control. Change one suspected cause while keeping the shared input fixed. For
an effort change, compare `A → A → B → B` and `B → B → A → A` on independent
prefixes. The first repeat checks baseline reuse, the switch tests reuse across
efforts, and the final repeat checks reuse at the new effort. If the unchanged
control fails to warm, investigate placement or cache eligibility before
attributing the miss to the changed field. Select the route source explicitly
and apply the skill's existing live-probe authorization and call bounds.

Record reported total, cached and uncached input and cache-write tokens when
available. Derive uncached input only when the provider's usage semantics allow
it. Treat omitted usage as unknown. Measure time to first token alongside first
useful output, completed-task latency, output tokens, model rounds and retries.
Evaluate per successful task on representative workloads and known billing
rates where available. A higher hit ratio can coexist with more billed tokens,
and a smaller reusable prefix can help even when fewer cached tokens are read.

## Fix the owning boundary

- Keep reusable instructions and eligible tool definitions stable where role,
  order and tool-selection behavior permit. Keep volatile diagnostics outside
  model input. Place fresh evidence in the appropriate later message and append
  tool results or new turns where the provider contract permits. Preserve
  freshness, instruction priority, history semantics and tool authorization.
- Test the existing fixed-effort alias against automatic routing when the
  evidence implicates effort changes. Preserve explicit caller effort and task
  quality. Favor fixes that keep provider selection in Switchyard. Preserve the
  agent's endpoint, public aliases and ordinary tool protocol so switching
  provider profiles requires no agent redeployment. Preserve cache isolation
  and test affinity changes as their own experiments.
- Evaluate provider-native features against the current workload, including
  existing provider-neutral MCP discovery. Weigh smaller prefixes against extra
  model rounds and continuation requirements. Keep any supported extension
  route-scoped with a compatible ordinary path. Verify the same agent build and
  settings with a second configured provider when a shared protocol, alias or
  routing path changes.

Use the [paired optimization loop](optimization-loop.md) to verify the fix on
representative multi-turn and tool-continuation tasks. Retain it only when the
measured benefit survives the quality and compatibility gates. Record the
provider, model, rendering or cache scope, measured gain and remaining unknowns
in the experiment ledger. Apply the skill's normal rollout authorization.
