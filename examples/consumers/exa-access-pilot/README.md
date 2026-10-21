# Consumer trial: choosing an anonymously usable Exa tool

**Prospective user:** the AgentAction maintainer who requested endpoint/tool
authentication distinctions in [Exa #425](https://github.com/exa-labs/exa-mcp-server/issues/425#issuecomment-5822803208).
This is a runnable opt-in trial, not an accepted integration or adoption.
Exa closed that metadata proposal as not planned; this trial changes neither
their registry record nor the AgentAction application.

## The actual decision

An agent needs ordinary web search, and its host has no Exa credential. Should
it offer `web_search_exa`, attempt `agent_run`, or stop for setup?

The current official registry's credential inputs remain unspecified. Absence
alone must stay unknown. Exa's separate provider documentation declares:

- anonymous hosted access with rate limits;
- optional OAuth/API keys for higher limits;
- required OAuth/API-key authentication for Exa Agent.

The adapter retains endpoint declarations separately from per-tool ASM
manifests. It feeds only explicit, fresh anonymous candidates to the real
`asm_protocol.selection.select` implementation. Configured-but-unverified
credentials never become account grants. The output is advisory and never
authorizes or executes a tool.

## Run it (Python 3.12)

From this repository checkout, without installing packages or providing a key:

```bash
# Two bounded public GitHub reads; no Exa tool call or model call.
python examples/consumers/exa-access-pilot/run.py \
  --task web_search --write-bundle /tmp/exa-access.json

# Same source snapshot, no extra network reads; must request setup, not select agent_run.
python examples/consumers/exa-access-pilot/run.py \
  --bundle /tmp/exa-access.json --task multi_step_research

# A configured credential is not evidence that this account may use the tool.
python examples/consumers/exa-access-pilot/run.py \
  --bundle /tmp/exa-access.json --task multi_step_research \
  --auth-context configured_unverified
```

If this machine needs its existing proxy, use ordinary `HTTPS_PROXY` configuration;
do not disable TLS checks. A provider-documentation change fails closed for
review. Saved snapshots expire after 24 hours; rerun the first command to fetch
current source facts rather than editing old timestamps. This bounded Exa
source adapter is not a universal documentation parser.

The callable integration is
`asm_protocol.integrations.access_preflight.access_preflight`.
Consumers may instead inspect the JSON examples before deciding whether to
integrate. Neither package installation nor a new service is required to review
the emitted contract. A hosted TypeScript integration is not implemented here.

## First external-use acceptance

This trial moves beyond an authored example only if the consumer maintainer:

1. runs it for an actual connection/setup or tool-choice decision;
2. confirms whether the selected basic tool or setup stop matches their real
   host state, retaining only a redacted decision receipt;
3. keeps it in that workflow for the next real decision, or reports why it was
   removed. No new decision is not itself churn.

Ask for one real use and one later reuse, not a star, link, or passing fixture.
Do not request credentials, raw task content or private logs. A reviewer running
the commands is a trial, not proof of production retention or savings.

## Costs and limits

The deterministic preflight makes zero additional model calls. Capture and
preflight elapsed time are reported separately; capture costs are charged once,
and `source_http_reads_this_run` is zero when a bundle is reused. API dollars,
host-model dollars and development cost are not measured here and remain
unknown. No latency comparison, model-token saving or economic advantage is
claimed. Unknown provider prices remain unknown in the selector output.

The declarations are adapter-author interpretations of pinned public provider
documentation, not Exa-approved metadata. Anonymous *declaration* does not prove
current invocation success, quotas or completeness. The host must retain its
existing consent, auth, scope and side-effect controls. The module deliberately
does not turn a key's presence into verified access.

`evidence/` holds a public-source capture and three local integration runs.
They are source/consumer-code checks, not external adoption, paid execution or
an Agent-versus-Agent A/B experiment.
