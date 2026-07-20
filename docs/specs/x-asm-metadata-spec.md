# x-asm: MCP Tool Metadata Extension for Quality-Aware Agent Selection

> **Status**: Draft v0.1
> **Authors**: ASM Protocol Team
> **Last Updated**: 2026-04-14
> **Compatibility**: MCP v1.0+

> **2026-05 update**: For immediate MCP Registry adoption, prefer embedding the full ASM object in `server.json` at `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`. See [`docs/integrations/mcp-registry.md`](../integrations/mcp-registry.md). The older `x-asm` ToolAnnotations shape remains useful as a tool-level extension proposal, but registry-level metadata is the current recommended path.

## Abstract

This document proposes `x-asm` — a metadata extension for MCP (Model Context Protocol) Tool definitions that enables AI agents to make quality-aware, cost-optimized tool selection decisions at runtime. The extension adds structured pricing, SLA, quality, and trust metadata to MCP tools without breaking backward compatibility.

## Motivation

MCP has achieved massive adoption (97M+ monthly npm downloads, 20,000+ servers). However, agents currently have no structured way to:

1. **Compare** tools that serve the same purpose (e.g., two email-sending MCP servers)
2. **Evaluate** tool quality before invocation (latency, reliability, accuracy)
3. **Budget** tool usage costs (no pricing metadata exists in MCP spec)
4. **Trust** tool providers (no reputation or verification framework)

The MCP 2026 Roadmap explicitly calls for "Richer Tool Metadata" including pricing, reliability metrics, latency estimates, and trust scores. `x-asm` provides exactly this.

## Specification

### Extension Format

The `x-asm` extension is added to MCP Tool definitions via the `annotations` field (MCP v1.0+) or as a top-level extension property:

```json
{
  "name": "send_email",
  "description": "Send a transactional email via Resend API",
  "inputSchema": {
    "type": "object",
    "properties": {
      "to": { "type": "string" },
      "subject": { "type": "string" },
      "body": { "type": "string" }
    },
    "required": ["to", "subject", "body"]
  },
  "annotations": {
    "x-asm-version": "0.3",
    "x-asm-service-id": "resend/email-api@v1",
    "x-asm-taxonomy": "tool.communication.email",
    "x-asm-pricing": {
      "model": "per_call",
      "price_per_call": 0.0001,
      "currency": "USD"
    },
    "x-asm-sla": {
      "latency_p50_ms": 200,
      "latency_p99_ms": 800,
      "uptime": 0.999,
      "rate_limit": "1000 req/min"
    },
    "x-asm-quality": {
      "metrics": [
        {
          "name": "delivery_rate",
          "score": 0.997,
          "scale": "0-1",
          "self_reported": false
        }
      ]
    },
    "x-asm-trust": {
      "score": 0.91,
      "confidence": 0.85,
      "reports": 342,
      "last_updated": "2026-04-14T10:00:00Z"
    }
  }
}
```

### Field Definitions

#### `x-asm-version` (string, required)
ASM specification version. Current: `"0.3"`.

#### `x-asm-service-id` (string, required)
Globally unique service identifier. Format: `<provider>/<service>@<version>`.

#### `x-asm-taxonomy` (string, required)
Standardized service category. Format: `<domain>.<category>[.<subcategory>]`.

Examples: `ai.llm.chat`, `tool.communication.email`, `infra.database.vector`

#### `x-asm-pricing` (object, optional)
```typescript
interface XAsmPricing {
  model: "per_call" | "per_token" | "per_second" | "per_unit" | "free";
  price_per_call?: number;       // Cost per invocation
  price_per_input_token?: number; // Cost per input token (LLMs)
  price_per_output_token?: number;// Cost per output token (LLMs)
  currency: string;               // ISO 4217 (default: "USD")
  free_tier?: {
    limit: number;
    period: "daily" | "monthly";
  };
}
```

#### `x-asm-sla` (object, optional)
```typescript
interface XAsmSla {
  latency_p50_ms: number;   // Median latency in milliseconds
  latency_p99_ms?: number;  // 99th percentile latency
  uptime: number;           // 0-1 (e.g., 0.999 = 99.9%)
  rate_limit?: string;      // Human-readable (e.g., "1000 req/min")
  regions?: string[];       // Available regions
}
```

#### `x-asm-quality` (object, optional)
```typescript
interface XAsmQuality {
  metrics: Array<{
    name: string;           // Metric name (e.g., "accuracy", "FID", "MOS")
    score: number;          // Metric value
    scale: string;          // Score scale (e.g., "0-1", "Elo")
    benchmark?: string;     // Benchmark name
    self_reported: boolean; // true = provider-reported, false = independently verified
  }>;
}
```

#### `x-asm-trust` (object, optional)
```typescript
interface XAsmTrust {
  score: number;           // 0-1, computed by ASM Trust Delta engine
  confidence: number;      // 0-1, based on number of reports and recency
  reports: number;         // Total usage reports contributing to this score
  last_updated: string;    // ISO 8601 timestamp
}
```

Trust scores are **not self-reported**. They are computed by the ASM Trust Delta engine based on aggregated agent usage data. The formula uses exponential decay weighting:

```
trust = Σ(w_i × match_i) / Σ(w_i)
where w_i = e^(-λ × age_i) and match_i = 1 - |declared - actual| / declared
```

### Taxonomy Standard

The `x-asm-taxonomy` field follows a hierarchical naming convention:

```
ai.llm.chat              — Chat/conversational LLMs
ai.llm.embedding         — Embedding models
ai.vision.image_generation — Image generation
ai.vision.ocr            — OCR services
ai.audio.tts             — Text-to-speech
ai.audio.stt             — Speech-to-text
ai.video.generation      — Video generation
ai.nlp.translation       — Translation services
ai.code.completion       — Code completion
tool.communication.email — Email APIs
tool.communication.sms   — SMS APIs
tool.data.search         — Search APIs
tool.data.scraping       — Web scraping
tool.devops.deployment   — Deployment platforms
tool.devops.ci           — CI/CD pipelines
tool.devops.monitoring   — Monitoring/APM
tool.productivity.todo   — Task management
tool.productivity.calendar — Calendar APIs
infra.database.postgres  — SQL databases
infra.database.vector    — Vector databases
infra.database.kv        — Key-value stores
infra.compute.gpu        — GPU compute
infra.compute.sandbox    — Code execution sandboxes
```

Full taxonomy list: 47 categories covering the MCP ecosystem.

### Agent Usage Flow

```
1. Agent receives task: "Send an email to confirm the order"
2. Agent queries ASM: discover_services({ query: "email sending", weights: { cost: 0.3, reliability: 0.5 } })
3. ASM returns ranked list with x-asm metadata
4. Agent selects top-ranked tool (e.g., Resend with trust=0.91)
5. Agent invokes MCP tool normally
6. Agent reports usage: report_usage({ service_id: "resend/email-api@v1", actual_latency_ms: 185, success: true })
7. ASM updates trust score via Trust Delta
```

### Backward Compatibility

- MCP clients that don't understand `x-asm-*` annotations simply ignore them
- All `x-asm-*` fields are optional — servers can adopt incrementally
- The extension uses the standard MCP `annotations` field, no protocol changes needed

### Validation

Use `asm-lint` to validate x-asm metadata:

```bash
npx @asm-protocol/lint <mcp-server-command>
```

The linter checks:
- All required fields present
- Taxonomy matches known categories
- Pricing values are non-negative
- SLA values are within valid ranges
- Trust scores (if present) have valid confidence

## References

- [MCP Specification](https://modelcontextprotocol.io)
- [ASM Manifest Schema v0.3](https://github.com/YE-YI7/asm-spec/blob/main/schema/asm-v0.3.schema.json)
- [TOPSIS Multi-Criteria Decision Making](https://en.wikipedia.org/wiki/TOPSIS)
- [Trust Delta: Exponential Decay Weighted Scoring](https://github.com/YE-YI7/asm-spec/blob/main/payments/src/trust-delta.ts)
