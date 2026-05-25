# ASM for MCP Registry `server.json`

MCP Registry already gives agents a standard place to discover MCP servers. ASM adds the missing value layer: pricing, quality, SLA, payment, provenance, and verification metadata that agents can use before invocation.

The least disruptive integration path is to embed ASM under the MCP Registry publisher-provided `_meta` namespace:

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
        "pricing": { "billing_dimensions": [] },
        "quality": { "metrics": [] },
        "sla": { "latency_p50": "650ms", "uptime": 0.995 },
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

## Why `_meta`

- It is backward-compatible: MCP hosts that do not understand ASM ignore it.
- It is namespaced: ASM does not pollute MCP core fields.
- It is deployable today: publishers and aggregators can add/read it without waiting for a protocol change.
- It keeps MCP capability discovery and ASM value settlement separate.

Recommended key:

```text
_meta.io.modelcontextprotocol.registry/publisher-provided.asm
```

Optional pointer:

```text
_meta.io.modelcontextprotocol.registry/publisher-provided.asm_url
```

Use `asm_url` when the full manifest is too large for a registry metadata field or when the publisher wants a canonical `.well-known/asm` endpoint.

## Field mapping

| MCP Registry field | ASM field | Purpose |
|---|---|---|
| `name` | `service_id` | MCP package identity vs globally unique service/version identity |
| `description` | `capabilities.description` | Human-readable capability summary |
| `packages[]` / `remotes[]` | `provider`, `payment`, `verification` | How to install/invoke vs how to buy/verify value claims |
| `repository.url` | `provenance.source_url` | Code source vs value-claim source |
| `_meta` | full ASM object | Publisher-provided value metadata |

## Compatibility rules

- `asm` SHOULD be a valid ASM v0.3 manifest object.
- `asm_url` MAY point to the same manifest at `.well-known/asm`.
- Aggregators SHOULD treat missing ASM as a warning, not as an invalid MCP server.
- Aggregators SHOULD validate `asm` against `schema/asm-v0.3.schema.json`.
- Selectors SHOULD compare quality scores only within matching `quality.metrics[].name` / `benchmark` semantics.

## Validate an MCP `server.json`

```bash
asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json
```

Extract the embedded ASM manifest:

```bash
asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json \
  --write-out /tmp/remote-search.asm.json
```

Machine-readable output:

```bash
asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json --json
```

## Examples

- `examples/mcp-server-json/basic-with-asm.server.json`
- `examples/mcp-server-json/remote-with-asm.server.json`
- `examples/mcp-server-json/package-with-asm.server.json`
- `examples/mcp-server-json/operational-envelope-with-asm.server.json`

## Draft v0.4: pre-call operational envelope

ASM v0.3 focuses on value metadata: pricing, quality, SLA, provenance,
verification, payment, and receipts. Draft v0.4 adds an optional
`operational_constraints` object for pre-call policy inputs: rate limits,
quotas, spend caps, approval boundaries, risk class, side effects, and receipt
requirements.

This is still producer-provided metadata. ASM does not enforce local policy;
clients and registries decide how to use it.

Example:

```bash
asm-mcp-validate examples/mcp-server-json/operational-envelope-with-asm.server.json
```

RFC:
[`docs/rfcs/operational-envelope-v0.4.md`](../rfcs/operational-envelope-v0.4.md)
