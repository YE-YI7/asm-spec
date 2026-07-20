# Akkhar-Code × ASM Integration Brief

> **Original brief author**: Rahat Hasan, Akkhar-Labs Architecture
> **Original date**: 2026-05-16
> **Republished here**: 2026-05-16, with permission, full attribution.
> **Status**: Reference integration for [RFC: Trust Delta receipt extension v0.1](https://github.com/YE-YI7/asm-spec/issues).
> **Canonical home**: This document. If a newer revision exists upstream at Akkhar-Labs, this file links to it from the header.

This is the first external reference integration for ASM Trust Delta receipts. It is preserved verbatim from the brief delivered by Akkhar-Labs on 2026-05-16, with light editorial framing only (this header and the bottom cross-reference). Akkhar-Labs retains authorship of the receipt schema, seal construction, and identifier convention described below; ASM retains authorship of the Trust Delta consumption logic that ingests them.

---

## 1. Receipt JSON Shape

Akkhar-Code's Phase 4 (Atomic Execution) closes every pipeline run with an immutable **Execution Receipt**. This is the JSON shape a Trust Delta consumer would ingest.

```json
{
  "receipt_version": "0.1",
  "pipeline_id": "ak_pipe_8f3a1c9e-22b7-4d01-aef3-70bc4e5d99f1",
  "service_id": "akkhar-labs/akkhar-code@1.0",
  "model_id": "akkhar-labs/orchestrator-v1:phase4-executor",
  "timestamp_start": "2026-05-12T09:41:03.112Z",
  "timestamp_end": "2026-05-12T09:41:04.887Z",
  "duration_ms": 1775,
  "phase_summary": {
    "phase1_discovery": {
      "ambiguities_surfaced": 3,
      "ambiguities_resolved": 3,
      "skipped": false
    },
    "phase2_planning": {
      "file_operations_planned": 7,
      "refinement_iterations": 1,
      "estimated_complexity": "moderate"
    },
    "phase3_gating": {
      "decision": "approved",
      "approved_at": "2026-05-12T09:41:02.004Z"
    },
    "phase4_execution": {
      "status": "success",
      "operations_executed": 7,
      "operations_failed": 0,
      "rollback_performed": false,
      "bytes_written": 14382
    }
  },
  "plan_hash": "sha256:a1c4f89e3b…d702f",
  "seal": {
    "algorithm": "sha256",
    "scope": "execution_payload",
    "digest": "sha256:e4b2c91f7a…88d3e",
    "byte_range": "see §2"
  },
  "billing": {
    "dimension": "pipeline_run",
    "unit": "per_run",
    "quantity": 1,
    "input_tokens": 2840,
    "output_tokens": 11206,
    "currency": "USD",
    "cost": 0.0037
  },
  "outcome": {
    "files_created": 2,
    "files_modified": 4,
    "files_deleted": 1,
    "test_strategy_emitted": true
  }
}
```

### Field glossary

| Field | Type | Unit / Note |
|-------|------|-------------|
| `pipeline_id` | UUIDv4, `ak_pipe_` prefix | One per prompt-to-execution run |
| `service_id` | ASM-compatible string | See §3 for convention |
| `model_id` | Scoped identifier | Identifies the model + phase role |
| `duration_ms` | int | Wall-clock, Phase 1 start → Phase 4 commit |
| `phase_summary.*` | object | Per-phase counters; all phases always present |
| `plan_hash` | `sha256:hex` | Hash of the **approved** `ImplementationPlan` JSON |
| `seal.digest` | `sha256:hex` | Hash of the execution payload byte range (§2) |
| `billing.dimension` | string | Maps to ASM `pricing.billing_dimensions[].dimension` |
| `billing.input_tokens` / `output_tokens` | int | Aggregate across all 4 phases |
| `billing.cost` | float | Estimated; actual settlement via AP2/payment rail |

---

## 2. Seal: What It Computes Over

The seal covers a **canonical execution payload** — not the full receipt, and not the raw model output stream. The payload is constructed as follows:

```
SEALED_BYTES = canonical_json(
  pipeline_id            // 36 bytes UUID
  + plan_hash            // 32 bytes (raw SHA-256, not hex)
  + ordered_file_ops[]   // For each FileOperation in execution order:
      filepath (UTF-8)
      + action enum (1 byte: 0x01=create, 0x02=modify, 0x03=delete, 0x04=rename)
      + content_hash (32 bytes, SHA-256 of post-write file content)
  + timestamp_end        // 8 bytes, Unix epoch ms, big-endian
)
```

### Concrete example

```
pipeline_id:    ak_pipe_8f3a1c9e-22b7-4d01-aef3-70bc4e5d99f1
plan_hash:      a1c4f89e3b…d702f
file_ops[0]:    src/auth/middleware.ts | 0x01 (create) | sha256:ff91…
file_ops[1]:    src/routes/api.ts      | 0x02 (modify) | sha256:3a8c…
…
file_ops[6]:    src/old/legacy.ts      | 0x03 (delete) | sha256:0000…
timestamp_end:  2026-05-12T09:41:04.887Z → 1778603264887

seal.digest = sha256( canonical_json( above ) )
            = sha256:e4b2c91f7a…88d3e
```

### Design rationale

| Choice | Why |
|--------|-----|
| Hash **post-write content**, not diffs | Diffs are presentation; content hashes are deterministic and diffable offline |
| Include `plan_hash` in seal | Binds the receipt to the exact plan the human approved — tamper-evident chain from Phase 3 → Phase 4 |
| Exclude Phase 1/2 chat tokens | Those are advisory; only the approved plan and its execution are settlement-relevant |
| `0x00…` for deletes | Content hash of a deleted file is defined as the zero hash — no ambiguity |

### What this means for Trust Delta

A verifier can recompute the seal from the receipt fields + the post-write file content hashes. If `seal.digest` matches, the execution was faithful to the approved plan. If it doesn't, either the executor deviated or the receipt was tampered with.

---

## 3. Model Identifier Convention → ASM `service_id` Mapping

### Akkhar-Code's `model_id` format

```
{org}/{product}@{version}:{phase_role}
```

Examples:

| `model_id` | When used |
|------------|-----------|
| `akkhar-labs/akkhar-code@1.0:phase1-discovery` | Ambiguity detection + form generation |
| `akkhar-labs/akkhar-code@1.0:phase2-planner` | Implementation plan generation |
| `akkhar-labs/akkhar-code@1.0:phase4-executor` | Deterministic code write pass |
| `anthropic/claude-sonnet-4-20250514@1.0:phase2-planner` | If an external model backs a phase |

### Mapping to ASM `service_id`

The receipt-level `service_id` identifies the **pipeline as a whole**:

```
akkhar-labs/akkhar-code@1.0
```

This maps 1:1 to an ASM manifest with:

```json
{
  "asm_version": "0.3",
  "service_id": "akkhar-labs/akkhar-code@1.0",
  "taxonomy": "tool.code.orchestration",
  "pricing": {
    "billing_dimensions": [
      { "dimension": "pipeline_run",  "unit": "per_run", "cost_per_unit": 0.0037, "currency": "USD" },
      { "dimension": "input_tokens",  "unit": "per_1M",  "cost_per_unit": 3.00,   "currency": "USD" },
      { "dimension": "output_tokens", "unit": "per_1M",  "cost_per_unit": 15.00,  "currency": "USD" }
    ]
  }
}
```

### When a phase delegates to an external model

If Phase 2 planning is backed by, say, `openai/gpt-5@1.0`, the receipt includes a `delegates_to` array so Trust Delta can trace cost and quality back to the underlying ASM `service_id`:

```json
{
  "delegates_to": [
    {
      "phase": "phase2_planning",
      "asm_service_id": "openai/gpt-5@1.0",
      "model_id": "openai/gpt-5@1.0:phase2-planner",
      "tokens_consumed": { "input": 1200, "output": 4800 }
    }
  ]
}
```

This lets Trust Delta resolve the full cost stack: pipeline-level settlement via `akkhar-labs/akkhar-code@1.0`, with per-phase attribution to upstream model providers via their own ASM manifests.

---

## 4. ASM-side decisions (consolidated from RFC)

The four open questions from the original brief were resolved as follows. See the [RFC issue](https://github.com/YE-YI7/asm-spec/issues) for the full reasoning.

| # | Question | Decision |
|---|---|---|
| 1 | Receipt cadence | Push to consumer webhook (preferred), poll fallback. Envelope: `{receipts: [...], publisher, signature}`. Both modes interoperable. |
| 2 | `billing.cost` authority | Both: receipt cost = publisher claim; Trust Delta also recomputes from `token_counts × manifest.pricing` and surfaces the delta as a first-class trust signal. |
| 3 | Multi-model seal chaining | v0.1 minimum = pipeline-level seal sufficient for settlement. v0.2 full attribution = each `delegates_to` entry carries its own provider-signed seal; Trust Delta walks the chain. Opt-in. |
| 4 | Taxonomy | `tool.code.orchestration` added as new ASM taxonomy leaf in v0.3.2. Akkhar-Code's manifest is reserved for the leaf, pending Akkhar-Labs's own production-readiness timeline. |

---

## Cross-references

- RFC issue (canonical discussion): [Trust Delta receipt extension v0.1](https://github.com/YE-YI7/asm-spec/issues)
- ASM schema (v0.3): [`schema/asm-v0.3.schema.json`](../../schema/asm-v0.3.schema.json)
- ASM Trust Delta description in paper: §3.4, §6.3, §7.2 of [`paper/asm-paper-draft.md`](../../paper/asm-paper-draft.md)
- Akkhar-Labs: external party authoring the receipt format described here.

## License + attribution

This document is republished with permission of the original author. The receipt schema, seal construction, and `delegates_to` convention described in sections 1–3 are Akkhar-Labs' authorship and may be evolved by them independently. ASM commits to keeping this page current as a reference integration; if the authoritative version moves to an Akkhar-Labs-hosted URL, this page will link to it from the header above.
