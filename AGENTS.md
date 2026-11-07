# Daedalus monorepo

`submodules/daedalus-agent` and `submodules/daedalus-switchyard` form one model
request path. For routing, reasoning controls, provider transport, shared tool or
stream contracts, and end-to-end optimization, use
[daedalus-co-design](.agents/skills/daedalus-co-design/SKILL.md). Assess both sides
before changing a shared contract, even if only one requires an edit.

The task-classification levels are `max`, `xhigh`, `high`, `medium`, `low`, and `instant`.
Custom DeepSeek passthrough profiles are only `max`, `high`, `low`, and `instant`;
classification categories and provider settings are separate contracts.
`none` is retired as a public effort option. Verify actual provider behavior. Balance
quality, latency, and cost. Learn from bounded Kubernetes log reads in namespace
`daedalus` on each relevant skill run; no scheduled automation is configured.

Keep this shared skill and its sanitized lessons in the parent repository, not
personal skill directories or the agent's runtime skill catalog. Follow each
submodule's instructions for its code. Preserve unrelated work and independently
track changes, validation, and commits in the parent and each submodule.
