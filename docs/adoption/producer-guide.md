# Producer Guide: Add ASM to an MCP Server

This guide is for MCP server authors who want their service to be selectable by
agents on value, not only discoverable by capability.

The smallest useful integration is one optional ASM block under MCP Registry
`server.json` `_meta`. It does not change runtime behaviour. MCP hosts that do
not understand ASM ignore it.

## 1. Copy the minimal block

Put ASM under:

```text
_meta.io.modelcontextprotocol.registry/publisher-provided.asm
```

Minimal example:

```json
{
  "_meta": {
    "io.modelcontextprotocol.registry/publisher-provided": {
      "asm": {
        "asm_version": "0.3",
        "service_id": "your-org/your-mcp-server@1.0",
        "taxonomy": "tool.data.search",
        "display_name": "Your MCP Server",
        "provenance": {
          "source_url": "https://github.com/your-org/your-mcp-server",
          "retrieved_at": "2026-05-25T00:00:00Z",
          "last_verified_at": "2026-05-25T00:00:00Z",
          "verification_status": "self_reported",
          "notes": "Publisher-provided ASM metadata."
        },
        "pricing": {
          "billing_dimensions": [
            {
              "dimension": "request",
              "unit": "per_1K",
              "cost_per_unit": 0,
              "currency": "USD"
            }
          ]
        },
        "sla": {
          "rate_limit": "60 req/min"
        },
        "operational_constraints": {
          "risk_class": "low",
          "side_effects": ["external_api_call"],
          "approval": {
            "required": "never"
          },
          "receipt_required": false,
          "policy_notes": "Consumer policy remains authoritative."
        }
      }
    }
  }
}
```

## 2. Choose the taxonomy

Use the closest existing ASM taxonomy. Common MCP server cases:

| Server type | Suggested taxonomy |
|---|---|
| Web search / data lookup | `tool.data.search` |
| Browser automation | `tool.automation.browser` |
| Code execution / agentic IDE | `tool.code.orchestration` |
| CI or deployment automation | `tool.devops.ci` |
| LLM gateway / chat model | `ai.llm.chat` |
| TTS / speech | `ai.audio.tts` |
| Image generation | `ai.vision.image_generation` |

If none fits, open an issue proposing a taxonomy leaf.

## 3. Declare only what you can defend

Good ASM metadata is provenance-aware. Prefer a sparse but honest manifest over
a complete-looking manifest with placeholder numbers.

Recommended rules:

- If pricing is free, set `cost_per_unit: 0` and explain the quota or hosting
  assumptions in `provenance.notes`.
- If pricing depends on an upstream service, model the request cost if possible
  and document the upstream dependency.
- If latency is not measured, omit `latency_p50` rather than guessing.
- If quality is self-reported, set `self_reported: true`.
- If operational risk is unclear, use `risk_class: "medium"` and explain why.

## 4. Add the pre-call operational envelope

The draft v0.4 `operational_constraints` object is optional but useful. It
turns cost, rate limits, approval boundaries, and risk into pre-call metadata.

Recommended starter fields:

```json
{
  "operational_constraints": {
    "risk_class": "medium",
    "side_effects": ["external_api_call"],
    "approval": {
      "required": "conditional",
      "conditions": ["estimated_cost_usd > 1.00"]
    },
    "rate_limits": [
      {
        "dimension": "request",
        "limit": 60,
        "period": "minute",
        "scope": "account"
      }
    ],
    "receipt_required": false
  }
}
```

See the v0.4 draft RFC:
[`docs/rfcs/operational-envelope-v0.4.md`](../rfcs/operational-envelope-v0.4.md).

## 5. Validate

From an ASM checkout:

```bash
pip install -e .
asm-mcp-validate path/to/server.json
```

Machine-readable output:

```bash
asm-mcp-validate path/to/server.json --json
```

Extract the manifest:

```bash
asm-mcp-validate path/to/server.json --write-out /tmp/your-service.asm.json
```

Example to compare against:

```bash
asm-mcp-validate examples/mcp-server-json/operational-envelope-with-asm.server.json
```

## 6. Get listed as a reference integration

Open an issue in this repo with:

- Link to your `server.json` or `.well-known/asm`.
- Which fields are publisher-declared vs independently verified.
- Any fields you had to omit because the schema did not fit.
- Whether you emit receipts or only value metadata.

Reference integrations are listed in the README once the metadata is public and
validates. Partial integrations are acceptable if the provenance is clear.

## 7. What this gives aggregators

Producer-side ASM blocks let aggregators index value facets without guessing:

- pricing
- quotas and rate limits
- approval boundaries
- operational risk class
- provenance and verification state
- receipt support

The current registry adoption gate is coverage. The fastest way to make ASM
matter is for real MCP servers to publish small, honest ASM blocks that
aggregators can later index.
