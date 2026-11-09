# Recursive live co-design loop

The executable learner is `scripts/co_design_loop.py` (Python 3.11+). It runs on
demand, never on a schedule. Each iteration evaluates the current incumbent,
asks the answering LLM for one classifier edit using development results and
prior accepted/rejected feedback, validates that edit, and evaluates a candidate.
An accepted candidate becomes the next iteration's parent. A rejected candidate
leaves the incumbent intact; its failure informs the next proposal. It stops at
its iteration, plateau, request or wall-clock limit. No candidate is guaranteed
to improve the system.

## Joint contract

| Owner | Responsibility |
| --- | --- |
| Agent | Generic six-label schema; only configured profiles may be selected. The classifier has four categories; shipped agent profiles expose four; omission remains automatic. Emit a generated opaque correlation ID with each logical model call in logs and both request-ID headers. New agent loop retries/continuations get new IDs. Transport-internal retries retain that logical ID. Preserve authorization and conversation affinity separately. |
| Switchyard | Consume existing `x-switchyard-request-id`/`x-request-id` metadata, include it in routing spans, and forward the allowlisted request ID upstream. Its existing pinned implementation supports this; no gateway code change is required. |
| Learner | Send synthetic LAN probes, correlate exact IDs, measure stream completion and deterministic outcomes, propose one classifier-only change, evaluate paired trials and holdout, retain evidence and the best local policy. |
| Deployment | Verify correlation coverage on the running agent image. Mixed versions still serve requests; absent correlation is an explicit evidence gap. The learner does not deploy, publish, commit, or advance gitlinks. |

## Secure API key

Create a dedicated Daedalus API key and store it outside Git in a mode-0600 file,
for example `~/.config/daedalus/probe-api-key`. Pass **only its path** with
`--api-key-file`. The runner rejects group/world-readable files, reads the token
in-process, and sends it only to `--app-url`. It never puts the token in command
arguments, subprocess environments, artifacts or proposal prompts. HTTP redirects
are not followed, and HTTPS certificates are verified. Local storage is plaintext
protected by filesystem permissions; remove the file/revoke the key when retired.

## Probe the running services

```bash
uv run --python 3.12 --no-project python \
  .agents/skills/daedalus-co-design/scripts/co_design_loop.py \
  --routes submodules/daedalus-switchyard/routes_fireworks.toml \
  --gateway-url http://192.168.1.234:30260/v1 \
  --app-url https://daedalus.ddns.me/v1 \
  --api-key-file ~/.config/daedalus/probe-api-key \
  --context kubernetes-admin@kubernetes --probe-only
```

`--routes` is required. Discover available `routes_*.toml` files and select the
actual provider variant explicitly; the example uses Fireworks. Do not select
a provider by glob order or maintain an exhaustive provider list. Source/live mismatch invalidates
provider-effort comparisons even when public aliases match.

The gateway URL must point at the intended LAN NodePort. The application URL
exercises nginx, compatibility API authentication, queue, worker, backend and
routing. The compatibility API accepts `daedalus` only; configured explicit profile probes
therefore go directly to Switchyard. Synthetic probes do not replay user traffic.
The application probe requests a literal response and has no user-side tool
executor. Internal agent work is governed by deployed limits; the compatibility
API's final-answer token limit does not bound its internal model calls.

## Run recursive trials

Make the decision service reachable without changing cluster configuration:

```bash
kubectl --context kubernetes-admin@kubernetes -n daedalus \
  port-forward service/decision-api 33000:30000 --address 127.0.0.1
```

On a host that can execute the built Switchyard binary, add these arguments to
the probe command and remove `--probe-only`:

```text
--gateway-binary /absolute/path/to/switchyard-server
--decision-url http://127.0.0.1:33000/v1
--iterations 3 --patience 2 --repeats 2
--max-calls 80 --max-seconds 900 --max-tokens 4096
```

For a Linux binary on Docker Desktop, additionally specify
`--gateway-container-image IMAGE` containing the binary's runtime libraries,
and use `--decision-url http://host.docker.internal:33000/v1`. The runner mounts
the supplied binary/config read-only, publishes the candidate gateway only on
host loopback, and removes its container at the end of each trial. Use an
appropriate image for the binary architecture. The relay listens on a host port
reachable from Docker and requires a fresh random token. Stop the port-forward
after the experiment. It is not a production configuration change.

Each isolated gateway retains source target defaults, maps each of its configured target models to
the corresponding explicit `daedalus/<profile>` LAN alias, and sends answering
requests through a streaming recording relay to the NodePort. The real decision
service classifies each request and continuation. Outgoing profile/effort and
exact-ID classifier events are checked. This records the payload submitted to
the LAN gateway, not an independently observed provider-internal configuration.
Source and live routes must agree before interpreting effective provider effort.
The isolated gateway/relay overhead is present in both baseline and candidate;
compare those matched trials, not their absolute latency with direct probes.

## Evaluation and retention

`fixtures/probes.json` contains synthetic development and holdout tasks with
exact answer checks, allowed concrete target IDs, and a single harmless local tool.
Allowed targets must exist in the selected route file; classifier task-category
names are not necessarily selectable targets. A profile migration requires a
versioned fixture update and fresh baseline; preserve earlier reports unchanged.
The proposal model sees development fixtures/results and prior iteration
feedback. It never sees holdout fixtures/results, raw Kubernetes logs, private
conversations or credentials. A holdout pass/fail bit can inform future proposals;
this is adaptive validation, not an untouched final benchmark. Before production
promotion, use a fresh independent task set representative of actual work.
The small default suite validates the loop, not broad reasoning quality.
`fixtures/probes-regression.json` adds literal extraction, fixed arithmetic state
updates, dependency chains and tool-result relay. Select it with `--cases`.
These are reusable regressions, not a permanently untouched final benchmark.
Review allowed profiles against the existing rubric before running: executing a
fixed arithmetic sequence can be mechanical `low` work; explaining code is a
different deliverable. If a fixture expectation is wrong, preserve the original
run, version the correction, and restart the baseline. Never relabel a completed
candidate trial to manufacture an accepted improvement.

The target classifier categories are max, high, low and instant. The runner
rejects a selected classifier with a different inventory before live traffic.
Explicit passthrough aliases and provider-native reasoning values are independent.

Only one of `instructions`, `choices.<profile>.criteria`, or
`choices.<profile>.min_probability` may change. The parsed TOML must differ only
at that field. Endpoints, models, public profiles, tools, tests, gates, budgets
and credentials cannot be changed by a proposal. No generated code or shell runs.

A candidate must pass every answer/tool/routing check. Restoring failed quality or
routing can qualify; otherwise **every** paired sample must improve latency by
at least 15% without a token or retry regression. Unknown usage blocks that
latency promotion. A latency winner must repeat the gain with candidate-first
ordering. The holdout must pass and stay within a 25%/one-second latency tolerance.
No dollar savings are claimed without provider pricing/billing. Treat missing
logs, failed baseline transport or truncated streams as gaps/failures, not wins.

All artifacts are private and ignored under `.artifacts/daedalus-co-design/`:
source/sandbox/candidate TOML, actual outgoing parameters, per-case metrics,
classifier logs, iteration ledger, optional `best.toml`, Kubernetes capture and
report. Rejected policies remain evidence, never become the next parent. The
best artifact is **not** written into the selected source route file or deployed. Promote a
validated policy with the normal reviewed change/rollout, then repeat full-path
probes using the deployed build and new heldout cases.

Hard ceilings: 8 iterations, 5 repeats, 250 runner-issued LAN/application calls,
3600 seconds of probe/optimization work, 180 seconds per request, 8192 requested
output tokens per call, 2 MiB per response. Capture/cleanup has separate bounded
deadlines. Gateway/provider or backend internal retries are not counted as
separate runner-issued calls. There is no automatic HTTP retry in the runner.

Run offline checks with:

```bash
uv run --python 3.12 --no-project python \
  .agents/skills/daedalus-co-design/scripts/test_co_design_loop.py
```

Also run the built agent/gateway `check_effort_boundary.py --routes <selected-file>`
with both binary arguments. Its synthetic provider supports Chat routes (Fireworks
and Baseten); native OpenAI Responses transport needs a separate fixture. It verifies logical
call-ID propagation through tool continuations and transport retry, plus all
public effort and failure contracts. Reconcile reusable findings into
`references/learning.md` after each run. Candidate acceptance alone is not a
verified production lesson.
