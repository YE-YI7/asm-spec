# Agent Service Manifest (ASM)

**MCP tells agents what services can do. ASM tells agents what services are worth.**

ASM helps agents choose services before calling them. It ranks APIs by pricing, quality, SLA, provenance, verification, payment, and pre-call operational constraints.

The fastest way to try it is as an OpenRouter value router:

```bash
pip install -e .
asm openrouter 'cheap coding model under $0.50 per 1M tokens'
asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'
```

This builds ephemeral ASM manifests from OpenRouter's public model metadata, ranks real model endpoints, and can emit router config snippets for tools you already use.

```bash
asm score "cheap reliable TTS under 1s"
```

Older equivalent form:

```bash
asm score --source openrouter 'cheap LLM under $1 per 1M tokens under 1s'
```

![ASM OpenRouter CLI demo](docs/assets/asm-openrouter-demo.gif)

If your Python script directory is not on `PATH`, use:

```bash
python -m asm_cli score "cheap reliable TTS under 1s"
python -m asm_cli score --source openrouter 'cheap LLM under $1 per 1M tokens under 1s'
```

ASM is MCP-compatible today: publish a standalone `.well-known/asm`, or embed ASM in MCP Registry `server.json` under `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`.

Current adoption wedge: make ASM useful as an intermediate value layer first. OpenRouter model selection is the first live target; producer-side MCP blocks remain the compatibility path once publishers want their services to be ranked.

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
