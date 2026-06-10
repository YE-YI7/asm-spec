# Agent Service Manifest (ASM)

**MCP tells agents what services can do. ASM tells agents what services are worth.**

ASM is the value-metadata layer for **agent tool selection**. When an agent carries out a task for a human, it faces many candidate tools — GUI apps, CLIs, and APIs; free and paid; cloud and local-only. ASM gives it the structured metadata to quickly pick one it *can actually drive*, is *allowed* to use, and that *fits the task* — then rank the survivors on cost, quality, latency, and data terms.

It is **not** a model picker. The tools are real products — task managers, design apps, data tools, schedulers — anything an agent might invoke on a user's behalf.

## Try it: pick a tool for a task

```bash
git clone https://github.com/calebguo007/asm-spec.git && cd asm-spec
python library/select_demo.py
```

For *"make a study plan and remind me daily"* with a cloud agent on Windows, the selector drops the tools it can't drive (Apple Reminders, Things 3 — local-device only) and the ones it can't call directly (Any.do — Zapier only), then ranks the rest. Ask for a built-in pomodoro and the pick changes to TickTick. Ask to *"edit an image and lay out a poster"* and it picks free, scriptable **Photopea** over paid Photoshop — and filters **Affinity Designer**, which exposes no automation API at all.

The library it selects over is in [`library/`](library/) — 26 real tools across task management, creative design, research, communication, developer tools, and booking/travel today, each carrying:

- **invocation** — can an agent drive it, and from where (cloud API / local script / GUI-only)
- **pricing**, **quality**, **sla**, **payment**
- **usage_terms** — whether automated use is even permitted
- **data_governance** — ownership, export, whether it trains on your data

Entries are schema-validated and source-linked; unverified dimensions are marked, not faked.

June 2026 coverage update: the tool-selection library now includes 26 source-linked tools across task management, creative design, research, communication, developer tools, and booking/travel. Booking and messaging entries deliberately expose `operational_constraints` so agents can separate read-only search from approval-gated actions such as sending messages, creating PRs, or purchasing flights.

Productization/distribution plan: [`docs/productization-distribution.md`](docs/productization-distribution.md).

Coverage report and remaining unknowns: [`docs/library-coverage-report.md`](docs/library-coverage-report.md).

## The gap ASM fills

The discovery layer is crowded — MCP / Server Cards, Zapier (8000+ apps), Composio (850+) all tell an agent *how to connect* to a tool. None tells it *which of several to pick*. We audited 14,519 entries across five MCP registries/directories: **0** expose pricing + SLA + quality + payment together in machine-actionable form. ASM is that missing value/selection layer — and it rides on top of the connection layers, not against them.

ASM is MCP-compatible: publish a standalone `.well-known/asm`, or embed ASM in MCP Registry `server.json` under `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`.

## Use it from an agent (MCP server)

ASM ships an MCP server so any MCP client (Claude Desktop, Cursor, an agent host) can call the selector as a tool — no schema adoption required:

```bash
git clone https://github.com/calebguo007/asm-spec && cd asm-spec
pip install mcp
python asm_selector_mcp.py        # stdio MCP server
```

It exposes three tools: **`select_tool`** (pick a tool for a task and return its risk/approval policy), **`list_library_tools`**, and **`get_tool_manifest`**. Point your client's MCP config at `python /path/to/asm-spec/asm_selector_mcp.py`; the selector reads `library/` (override with `ASM_LIBRARY_DIR`). The same selector is importable directly: `from library_select import select`.

The same engine is also available as:

```bash
# CLI (human or scripted)
asm select "find and book a refundable flight" --taxonomy tool.booking.travel \
  --requires flight_search,flight_order_create --json

# Hosted HTTP API (stdlib-only; deploy anywhere that runs Python)
python asm_select_api.py     # POST /select, GET /tools, GET /healthz on :8787
```

## One slice: ranking AI services (OpenRouter)

The same engine works for the AI-service taxonomy. No clone, no install (needs [uv](https://docs.astral.sh/uv/)):

```bash
uvx --from git+https://github.com/calebguo007/asm-spec.git \
  asm openrouter 'best value coding model under $3 per 1M tokens'
```

It builds ephemeral ASM manifests from OpenRouter's live model metadata, scores them on price vs. quality (LMArena Elo), and can emit a router config (LiteLLM / Vercel AI SDK / LangChain). Model routing is the easiest slice to demo — one taxonomy among many, not the point.

![ASM OpenRouter CLI demo](docs/assets/asm-openrouter-demo.gif)

Latest paper signals:

- 0/50 MCP-related GitHub repos and 0/14,519 registry/directory entries expose complete value metadata.
- 75 source-linked manifests across 47 taxonomies validate against `schema/asm-v0.3.schema.json`.
- Raw-doc LLM selection reaches 63.9-72.2% top-1 accuracy; ASM-manifest selection reaches 100.0%.
- Live execution shows ASM works only when quality metrics are semantically comparable; mixed benchmark scales are a real failure mode.
- External Arena/OpenRouter analysis is reported as a stress test, not a claim that any quality metric is universally correct.

Long-form results: [`docs/paper-results.md`](docs/paper-results.md). Reproducibility map: [`ARTIFACT.md`](ARTIFACT.md).

---

## Try ASM in 60 Seconds

```bash
git clone https://github.com/calebguo007/asm-spec.git
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
| **Akkhar-Code** (Akkhar-Labs) | Agentic IDE, `tool.code.orchestration` | Trust Delta receipt extension v0.1 | [`docs/integrations/akkhar-code-receipt-spec.md`](docs/integrations/akkhar-code-receipt-spec.md) · [reference receipt](examples/receipts/akkhar-code-receipt.json) · RFC [#7](https://github.com/calebguo007/asm-spec/issues/7), PR [#8](https://github.com/calebguo007/asm-spec/pull/8) |

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
library/                        Tool-value library (agent tool selection) + select_demo.py
manifests/                      75 source-linked manifests
scorer/                         Python TOPSIS scorer and tests
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
Open starter issues: [Cohere](https://github.com/calebguo007/asm-spec/issues/1), [Mistral AI](https://github.com/calebguo007/asm-spec/issues/2), [Together AI](https://github.com/calebguo007/asm-spec/issues/3), [Groq](https://github.com/calebguo007/asm-spec/issues/4), [Fireworks AI](https://github.com/calebguo007/asm-spec/issues/5).

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
  howpublished={\url{https://github.com/calebguo007/asm-spec}}
}
```

---

## License

MIT. See [`LICENSE`](LICENSE).
