# Daedalus monorepo

`submodules/daedalus-agent` and `submodules/daedalus-switchyard` form one model
request path. The agent calls `submodules/daedalus-sandbox` directly for code
execution and offline linting/verification. For routing, reasoning controls,
provider transport, shared tool or stream contracts, sandbox integration,
context ingestion/retrieval and information-layer integration, and
end-to-end optimization, use
[daedalus-co-design](.agents/skills/daedalus-co-design/SKILL.md). Assess affected
owners and consumers before changing a shared contract, even if only one needs an edit.

`submodules/daedalus-context` provides the agent's information layer: document
ingestion, vector retrieval, embeddings/reranking, and infrastructure MCP services.
Its Hindsight integration is externally owned. Context-service calls go directly
from the agent; Switchyard owns the model continuation using their results.
Assess the relevant paths across all four repositories without broadening an
isolated task into a full-stack audit.

The target task-classification levels are `max`, `high`, `low`, and `instant`.
Discover Switchyard provider configurations through `routes_*.toml`; require an
explicit selection for probes and deployment. Classification categories, public
passthrough aliases and provider-native reasoning settings are separate contracts.
Generic agent validation and provider-specific aliases may support extra levels.
`none` is retired as a public effort option. Verify actual provider behavior. Balance
quality, latency, and cost. Learn from bounded Kubernetes log reads in namespace
`daedalus` on each relevant skill run; no scheduled automation is configured.

Keep this shared skill and its sanitized lessons in the parent repository, not
personal skill directories or the agent's runtime skill catalog.
`.claude/skills/daedalus-co-design` is a relative symlink to that `.agents/skills`
directory so Claude Code discovers the skill; edit the source, not the link. Follow each
submodule's instructions for its code. Preserve unrelated work and independently
track changes, validation, and commits in the parent and each submodule.
