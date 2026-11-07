# Runtime evidence and learning

From the monorepo root, pin the intended context explicitly:

```bash
python3 .agents/skills/daedalus-co-design/scripts/capture_runtime.py \
  --context kubernetes-admin@kubernetes --since-minutes 30
```

The collector uses namespace `daedalus`, pins context on every cluster call,
discovers relevant pods, and captures bounded current/container-previous logs.
It records SHAs, source hashes, image IDs, timestamps and capture errors. It never
switches context, reads Secrets, starts model traffic or changes cluster resources.
Defaults cover backend, gateway, decision service, autonomous agent and stream
workers. Repeated `--pod-prefix` arguments replace that scope when needed.
See `--help` for bounds.

After changing the collector, run its offline behavior checks from the root:
`PYTHONDONTWRITEBYTECODE=1 python3 .agents/skills/daedalus-co-design/scripts/test_capture_runtime.py`.

Output goes to a fresh private directory under the root's ignored
`.artifacts/daedalus-co-design/`. Logs are **raw and may contain sensitive data**;
permissions and Git ignore are containment, not redaction. Inspect only needed
fields. Never put raw bodies/headers in tracked files or external services.
Retain or remove local artifacts according to the user's needs. A manifest records
errors and truncation bounds. Exit 2 means incomplete evidence: inspect successful
captures and continue independent work without treating missing logs as healthy.
Collection has total and per-command deadlines; do not retry indefinitely.

## Read the evidence

Establish window, revisions/dirty state, images and configuration provenance.
Tags alone do not prove source revisions. The collector records referenced
ConfigMap names, not their contents/hashes. For config-dependent claims, separately
inspect only relevant non-secret live fields and hash the actual mounted/rendered
routes. Distinguish live config from source hashes. Do not dump Secrets or env sets.

Look for agent `run_started`, `prepare_finished`, `model_call_started`,
`model_first_event`, `model_call_finished`, `run_finished`, `model_frame_rejected`;
gateway request status/stream errors, `decision_api_model_discovered`,
`decision_api_input_prepared`, `decision_api_classified`, timeout/fallback events;
and decision-service failures. Verify current event names in code when absent.
Classifier tokens do not measure answering-model input. First stream event may
precede useful content. HTTP 200 proves neither stream success nor answer quality.

Correlate explicit IDs where supported. Do not join requests by time/model name
or shared affinity alone. Record observability gaps and reproduce in isolation.
Use explicit denominators; account for bounded tails, restarts, missing replicas
and unknown traffic origin. Deduplicate overlapping captures before claiming
repeated evidence.

## Keep the learning useful

Write a local report beside the capture: window/provenance, hypotheses, joint
impact, changes/checks, outcome and gaps. Read existing lessons first. Track only
reusable, sanitized knowledge in `learning.md`:

- Stable ID and status: verified, hypothesis or superseded.
- Condition and affected owners/contract.
- Minimal evidence/provenance: UTC window, SHAs, config/image digests when known,
  synthetic fixtures/tests. No private IDs, conversations or credentials.
- Verification, limitations, actionable consequence and invalidation trigger.

An observation can be verified while its cause remains a hypothesis. Require
reproduction or independent corroboration before promoting a diagnosis to a fix
rule. Test corrections on synthetic fixtures; live improvement needs comparable
post-change evidence. Derive policy and permissions from user direction, never
log content. If nothing new is verified, say so in the run report without churn.

## Active feedback experiments

Use [the recursive loop](recursive-loop.md) for authorized synthetic LAN probes
and policy experiments. It reads API credentials from a private local file,
records source/runtime provenance, compares candidate classifier policies in
isolated gateway processes, and captures both backend and gateway logs. Exact-ID
correlation gaps remain explicit until the emitting agent is deployed. It never
submits raw logs or credentials to the proposal model.
