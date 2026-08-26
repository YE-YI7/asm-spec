# Agent Service Manifest (ASM)

**The agent economy has discovery and it's getting payment rails. The layer in between — deciding which tool an agent uses and who gets paid — is missing. ASM is our bid to build it.**

```
Discovery    MCP · ARD · AI-Catalog        what tools exist
    │
    ▼
Selection    ASM  ← the missing layer      which one the agent can use, should use, and pays
    │
    ▼
Settlement   x402 · AP2 · ACP              how the payment executes
```

The layers above and below are being built by Anthropic, Google, AWS, Coinbase, Visa. The **selection layer** between them — can the agent even drive this tool, is it allowed to, which of the eligible ones fits the task at what cost/quality/risk, and therefore who gets the work and the money — is the unfilled slot. ASM fills it with structured eligibility + value metadata (the substrate), a gated selector (the mechanism), and a hand-off to settlement.

It is **not** a model picker. The tools are real products — task managers, design apps, data tools, schedulers, booking APIs — anything an agent might invoke on a user's behalf.

**Honest status:** this is the layer we're *building*, with receipts (a measured benchmark, a working selector, a live on-chain demo below), not a layer with production traffic yet. We're early and say so.

## Validate your service in 60 seconds

ASM's adoption primitive is a deterministic lint report, not a universal score.
It accepts either a standalone ASM manifest or an MCP Registry `server.json`
with publisher-provided ASM metadata:

```bash
python -m pip install "asm-protocol==0.5.2"
asm-lint server.json --format markdown --output asm-lint-report.md
```

The report records schema validity, provenance completeness, claim freshness,
selection readiness, and a digest of the exact manifest inspected. Schema
errors fail CI by default; stricter projects can add `--fail-on not-ready`,
`--fail-on expired`, or `--fail-on stale`.

To keep the check enabled in GitHub Actions:

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - uses: YE-YI7/asm-spec/.github/actions/asm-lint@v0.5.2
    with:
      path: server.json
      fail-on: invalid
```

The Action adds the full Markdown report to the job summary. It does not call
an ASM-hosted API or upload the inspected manifest. See the
[lint and CI guide](docs/adoption/asm-lint.md) for status semantics.

## Try it: pick a tool for a task

```bash
git clone https://github.com/YE-YI7/asm-spec.git && cd asm-spec
python library/select_demo.py
```

The deterministic core does **not** pretend to understand the task sentence. The
caller supplies structured facts such as `taxonomy`, `required_functions`,
platform, reach, and expected workload; `task` remains audit/display text. If
taxonomy and required functions are both absent, selection returns
`under_specified` instead of choosing an unrelated globally cheap tool.

For *"make a study plan and remind me daily"* with a cloud agent on Windows, the selector drops the tools it can't drive (Apple Reminders, Things 3 — local-device only) and the ones it can't call directly (Any.do — Zapier only), then ranks the rest from those explicit constraints. Ask for a built-in pomodoro and the pick changes to TickTick. Ask to *"edit an image and lay out a poster"* and it filters **Affinity Designer**, which exposes no automation API at all.

The library it selects over is in [`library/`](library/) — 30 real tools across task management, creative design, research, communication, developer tools, booking, and real-estate data today, each carrying:

- **invocation** — can an agent drive it, and from where (cloud API / local script / GUI-only)
- **pricing**, **quality**, **sla**, **payment**
- **usage_terms** — whether automated use is even permitted
- **data_governance** — ownership, export, whether it trains on your data

Entries are schema-validated and source-linked; unverified dimensions are marked, not faked.

June 2026 coverage update: the tool-selection library now includes 30 source-linked tools across seven domains. Booking and messaging entries deliberately expose `operational_constraints` so agents can separate read-only search from approval-gated actions such as sending messages, creating PRs, or purchasing flights.

Productization/distribution plan: [`docs/productization-distribution.md`](docs/productization-distribution.md).

Coverage report and remaining unknowns: [`docs/library-coverage-report.md`](docs/library-coverage-report.md).

## The gap ASM fills

The discovery layer is crowded — MCP / Server Cards, Zapier (8000+ apps), Composio (850+) all tell an agent *how to connect* to a tool. None tells it *which of several to pick*. We audited 14,519 entries across five MCP registries/directories: **0** expose pricing + SLA + quality + an access/payment signal together in machine-actionable form. ASM is that missing selection layer — and it rides on top of the connection layers, not against them.

**Receipt that the layer is needed:** in [ToolSelect-Bench](benchmark/RESULTS.md), six frontier models choosing among real tools with only names vs. with ASM metadata — the metadata improved correct selection for **6/6** models and cut user-constraint violations for **5/6**; the strongest (GPT-5, Llama-3.3-70B) went from ~35% violations to ~8-10% and topped 90% correct. Honest caveat: gains are strongest on eligibility; the library skews to well-known tools, which *understates* long-tail value.

ASM is MCP-compatible: publish a standalone `.well-known/asm`, or embed ASM in MCP Registry `server.json` under `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`. Convention: inline blocks carry *static* facts; *mutable* value data (pricing/SLA/quality) should live behind `asm_url` so freshness has a single re-stampable source — guidance hardened by a production multi-server host (see [`docs/integrations/mcp-registry.md`](docs/integrations/mcp-registry.md)).

## Use it from an agent (MCP server)

ASM ships an MCP server so any MCP client (Claude Desktop, Cursor, an agent host) can call the selector as a tool — no schema adoption required:

```bash
python3 -m pip install "asm-protocol[mcp]==0.6.0"
asm-selector                     # stdio MCP server (MCP SDK 2.x)
```

It exposes three tools: **`select_tool`** (pick a tool for a task and return its risk/approval policy), **`list_library_tools`**, and **`get_tool_manifest`**. Point your client's MCP config at `asm-selector`, or at `python3 /path/to/asm-spec/asm_selector_mcp.py`; the selector reads `library/` (override with `ASM_LIBRARY_DIR`). The Python server uses the stable MCP SDK 2.x line and supports the modern `2026-07-28` protocol era. The same selector is importable directly: `from library_select import select`.

Cost output has an explicit `known`, `partial`, or `unknown` status. Metered
prices need expected monthly usage; one-time licenses need an amortization
period; prose-only free tiers remain unknown because their allowance and reset
rules are not machine-readable. If every eligible candidate does not have a
known cost in the same currency, the selector returns `needs_cost_facts` rather
than guessing. A caller may explicitly request the `capability_breadth` fallback;
it is never applied implicitly.

The same engine is also available as:

```bash
# CLI (human or scripted)
asm select "find and book a refundable flight" --taxonomy tool.booking.travel \
  --requires flight_search,flight_order_create --fallback-policy capability_breadth --json

# Hosted HTTP API (stdlib-only; deploy anywhere that runs Python)
python asm_select_api.py     # POST /select, GET /tools, GET /healthz on :8787
```

DeepSeek Harness developer-preview users can install the native
[`asm_select` tool adapter](integrations/deepseek-harness/README.md). It uses
the same HTTP contract and returns an unsigned Selection Receipt, but never
invokes or authorizes the selected service. The adapter defaults to a local
selector so task text is not sent to a hosted endpoint implicitly.

LangChain / LangGraph builders get the same selector as a drop-in tool (`pip install langchain-core`):

```python
import sys; sys.path += ["asm-spec", "asm-spec/integrations/langchain"]
from asm_tools import ASMToolSelectorTool
agent_tools = [ASMToolSelectorTool()]   # name: asm_tool_selector
```

A public reference instance runs at **https://asm-spec.onrender.com**. It also dogfoods ASM's own publishing convention: `GET /.well-known/asm` serves the library catalog (one re-stampable `generated_at`, per-manifest links), and `GET /manifest/{service_id}` serves each full manifest — ASM is its own first publisher.

```bash
curl -X POST https://asm-spec.onrender.com/select -H "Content-Type: application/json" \
  -d '{"task":"find and book a refundable flight","taxonomy":"tool.booking.travel",
       "required_functions":["flight_search","flight_order_create"],
       "require_approval_for":["financial_charge"]}'
# -> {"selected": {"display_name": "Amadeus Self-Service APIs", ...},
#     "risk_class": "critical", "approval_required": true, ...}
```

## One slice: ranking AI services (OpenRouter)

The same engine works for the AI-service taxonomy. No clone, no install (needs [uv](https://docs.astral.sh/uv/)):

```bash
uvx --from git+https://github.com/YE-YI7/asm-spec.git \
  asm openrouter 'best value coding model under $3 per 1M tokens'
```

It builds ephemeral ASM manifests from OpenRouter's live model metadata, scores them on price vs. quality (LMArena Elo), and can emit a router config (LiteLLM / Vercel AI SDK / LangChain). Model routing is the easiest slice to demo — one taxonomy among many, not the point.

![ASM OpenRouter CLI demo](docs/assets/asm-openrouter-demo.gif)

Latest paper signals:

- 0/50 MCP-related GitHub repos and 0/14,519 registry/directory entries expose complete value metadata.
- 75 source-linked manifests across 47 taxonomies validate against `schema/asm-v0.3.schema.json`.
- Raw-doc LLM selection reaches 63.9-72.2% top-1 accuracy; ASM-manifest selection reaches 100.0%.
- ToolSelect-Bench (6 frontier models, names-only vs ASM metadata): correct selection up for 6/6, violations down for 5/6; best models >90% correct, violations to ~8-10%.
- Live execution shows ASM works only when quality metrics are semantically comparable; mixed benchmark scales are a real failure mode.
- External Arena/OpenRouter analysis is reported as a stress test, not a claim that any quality metric is universally correct.

Long-form results: [`docs/paper-results.md`](docs/paper-results.md). Reproducibility map: [`ARTIFACT.md`](ARTIFACT.md).

---

## Try ASM in 60 Seconds

```bash
git clone https://github.com/YE-YI7/asm-spec.git
cd asm-spec
pip install -e .
asm openrouter 'cheap coding model under $0.50 per 1M tokens'
```

Example output shape:

```text
Selected: MoonshotAI: Kimi K2.6 (free)
Model: moonshotai/kimi-k2.6:free
Reason: MoonshotAI: Kimi K2.6 scored 1.000 via TOPSIS...

Ranked services:
1. MoonshotAI: Kimi K2.6 (free) (...)
2. Tencent: Hy3 preview (...)
3. StepFun: Step 3.5 Flash (...)

Rejected by hard constraints: none
```

Emit a LiteLLM router snippet:

```bash
asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'
```

Other export formats:

```bash
asm openrouter --format json 'best value model for long-context summarization'
asm openrouter route --format vercel-ai-sdk 'high quality reasoning model'
asm openrouter route --format langchain 'cheap reliable chat model'
```

OpenRouter value-router notes: [`docs/openrouter-value-router.md`](docs/openrouter-value-router.md).

Local manifest demo:

```bash
asm score "cheap reliable TTS under 1s"
```

Validate an MCP `server.json` with embedded ASM:

```bash
asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json
```

Validate a draft v0.4 pre-call operational envelope:

```bash
asm-mcp-validate examples/mcp-server-json/operational-envelope-with-asm.server.json
```

If the console script is not on `PATH`, use:

```bash
python -m mcp_server_json_asm examples/mcp-server-json/remote-with-asm.server.json
```

Try OpenRouter live model ranking:

```bash
asm openrouter 'cheap LLM under $1 per 1M tokens under 1s'
```

This builds ephemeral ASM manifests from OpenRouter's public `/api/v1/models`
metadata and merges the checked-in OpenRouter usage-ranking snapshot as a
revealed-preference signal. OpenRouter does not expose per-model latency in
that endpoint, so ASM reports and ignores latency hard constraints for this
source unless `--strict-latency` is set.

Extract the embedded ASM manifest:

```bash
asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json \
  --write-out /tmp/remote-search.asm.json
```

---

## Add ASM to Your MCP Server

### Option 1: publish `.well-known/asm`

Serve a normal ASM manifest:

```text
https://your-service.example/.well-known/asm
```

### Option 2: embed ASM in MCP Registry `server.json`

```json
{
  "name": "io.example/search",
  "description": "Search MCP server",
  "_meta": {
    "io.modelcontextprotocol.registry/publisher-provided": {
      "asm": {
        "asm_version": "0.3",
        "service_id": "example/search@1.0",
        "taxonomy": "tool.data.search",
        "pricing": {
          "billing_dimensions": [
            { "dimension": "query", "unit": "per_1K", "cost_per_unit": 2.5, "currency": "USD" }
          ]
        },
        "sla": { "latency_p50": "650ms", "uptime": 0.995 },
        "quality": {
          "metrics": [
            { "name": "answer_relevance", "score": 0.91, "scale": "0-1", "self_reported": true }
          ]
        },
        "provenance": {
          "source_url": "https://example.com/pricing",
          "retrieved_at": "2026-05-08T00:00:00Z",
          "last_verified_at": "2026-05-08T00:00:00Z",
          "verification_status": "self_reported"
        }
      },
      "asm_url": "https://example.com/.well-known/asm"
    }
  }
}
```

Full guide: [`docs/integrations/mcp-registry.md`](docs/integrations/mcp-registry.md).

Producer adoption guide: [`docs/adoption/producer-guide.md`](docs/adoption/producer-guide.md).

Draft v0.4 operational envelope RFC:
[`docs/rfcs/operational-envelope-v0.4.md`](docs/rfcs/operational-envelope-v0.4.md).

Examples:

- [`examples/mcp-server-json/basic-with-asm.server.json`](examples/mcp-server-json/basic-with-asm.server.json)
- [`examples/mcp-server-json/remote-with-asm.server.json`](examples/mcp-server-json/remote-with-asm.server.json)
- [`examples/mcp-server-json/package-with-asm.server.json`](examples/mcp-server-json/package-with-asm.server.json)
- [`examples/mcp-server-json/operational-envelope-with-asm.server.json`](examples/mcp-server-json/operational-envelope-with-asm.server.json)

---

## Reference Integrations

Real third-party services that have implemented ASM-compatible value metadata or receipt formats. Each one ships a spec page in this repo plus, where applicable, a reference receipt example.

| Service | Type | Status | Spec |
|---|---|---|---|
| **Akkhar-Code** (Akkhar-Labs) | Agentic IDE, `tool.code.orchestration` | Trust Delta receipt extension v0.1 | [`docs/integrations/akkhar-code-receipt-spec.md`](docs/integrations/akkhar-code-receipt-spec.md) · [reference receipt](examples/receipts/akkhar-code-receipt.json) · RFC [#7](https://github.com/YE-YI7/asm-spec/issues/7), PR [#8](https://github.com/YE-YI7/asm-spec/pull/8) |

If you're implementing ASM (manifest, `.well-known/asm` endpoint, or a receipt emitter) and want a reference-integration row, open an issue with `integration` label.

---

## Manifest Template

Only three fields are required; value metadata is optional but makes the service rankable.

```json
{
  "asm_version": "0.3",
  "service_id": "provider/service@version",
  "taxonomy": "tool.data.search",
  "display_name": "Service Name",
  "provenance": {
    "source_url": "https://provider.example/pricing",
    "retrieved_at": "2026-05-08T00:00:00Z",
    "last_verified_at": "2026-05-08T00:00:00Z",
    "verification_status": "self_reported",
    "notes": "Where pricing, SLA, and quality claims came from."
  },
  "pricing": {
    "billing_dimensions": [
      { "dimension": "request", "unit": "per_1K", "cost_per_unit": 1.0, "currency": "USD" }
    ]
  },
  "quality": {
    "metrics": [
      { "name": "task_success_rate", "score": 0.9, "scale": "0-1", "self_reported": true }
    ]
  },
  "sla": {
    "latency_p50": "500ms",
    "uptime": 0.99,
    "rate_limit": "60 req/min"
  },
  "payment": {
    "methods": ["stripe", "api_key_prepaid"],
    "auth_type": "api_key",
    "signup_url": "https://provider.example/signup"
  }
}
```

Schema: [`schema/asm-v0.3.schema.json`](schema/asm-v0.3.schema.json).

---

## Repository Map

```text
schema/                         ASM JSON Schema
src/asm_protocol/               Canonical Python SDK: selection, cost, version
library/                        Tool-value library (agent tool selection) + select_demo.py
manifests/                      75 source-linked manifests
scorer/                         Legacy experimental per-unit TOPSIS scorer and tests
registry/                       MCP registry server exposing ASM tools
examples/mcp-server-json/       MCP Registry server.json examples
docs/integrations/              MCP Registry and aggregator integration docs
experiments/                    Audit, selection, LLM, live, and external stress-test scripts
paper/                          Paper draft
ARTIFACT.md                     Claim-to-artifact reproducibility map
```

---

## Reproduce the Paper Numbers

```bash
pip install -r requirements.txt
make reproduce
```

Live LLM/API experiments require external credentials and are documented separately in `ARTIFACT.md`.

---

## Design Principles

1. Backward-compatible with MCP.
2. Minimal required fields: `asm_version`, `service_id`, `taxonomy`.
3. Value metadata is structured, source-linked, and auditable.
4. Quality metrics preserve their original benchmark semantics.
5. ASM declares value; AP2/payment systems execute settlement; receipts verify what happened.

---

## Contributing

Good first issues: [`docs/good-first-issues.md`](docs/good-first-issues.md).
Open starter issues: [Cohere](https://github.com/YE-YI7/asm-spec/issues/1), [Mistral AI](https://github.com/YE-YI7/asm-spec/issues/2), [Together AI](https://github.com/YE-YI7/asm-spec/issues/3), [Groq](https://github.com/YE-YI7/asm-spec/issues/4), [Fireworks AI](https://github.com/YE-YI7/asm-spec/issues/5).

Common contribution paths:

- Add a source-linked manifest.
- Embed ASM in an MCP `server.json`.
- Report stale pricing/SLA/quality metadata.
- Propose a taxonomy or benchmark compatibility rule.
- Build an aggregator import script.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Citation

```bibtex
@misc{asm2026,
  title={Agent Service Manifest: Value-Aware Settlement for Autonomous Service Selection},
  author={Guo, Yi},
  year={2026},
  howpublished={\url{https://github.com/YE-YI7/asm-spec}}
}
```

---

## License

MIT. See [`LICENSE`](LICENSE).
