# Release Notes: v0.3.2

ASM v0.3.2 turns the protocol from a self-contained paper artifact into one with **shipped external participation**. The receipt-emission shape is now formal, the trust-delta primitive has a production-grade upstream consumer, and the first external reference-integration partner is publicly tracked.

## What's new since v0.3.1

### Receipt envelope schema v0.1

- `schema/asm-receipt-envelope-v0.1.schema.json` (new) — canonical envelope for delivering Trust Delta receipts from publisher to consumer. Specifies push (POST to consumer's `payment.receipt_endpoint`) and poll (GET on publisher's `.well-known/asm-receipts`).
- Pinned algorithms in v0.1: Ed25519 for signatures, sha256 for seal digests. Pluggable algorithm list deferred to v0.2.
- Optional `signature.public_key_fingerprint` for key-substitution resistance at the `public_key_url`.
- `supersedes` field on receipt body — when a publisher needs to correct a receipt (e.g. wrong cost calculation), they emit a new receipt referencing the original's `pipeline_id`. The original is never mutated; Trust Delta receives an explicit correction signal instead of a silent overwrite.
- `delegates_to` chain for pipelines that wrap sub-services. v0.1 minimum: pipeline-level seal sufficient. v0.2 (future): each delegate carries its own provider-signed receipt for end-to-end verification.
- `retry_advisory` block — publishers can advertise their expected push retry semantics (1s initial, 2x backoff, 5 retries, 6h dead-letter as documented defaults).

### `cost_delta_from_receipt` primitive

- New function in `scorer/scorer.py`. Recomputes cost from `manifest.pricing.billing_dimensions × observed token counts` and returns the **aggregate** signed delta between the publisher's claimed cost and the manifest-implied cost, plus a per-dimension diagnostic.
- Aggregate (not per-dimension) is the trust signal — per-dimension is preserved as diagnostic only. This decision is from the RFC §2.4 discussion with the integration partner.
- Three unit tests added: agreement (delta ≈ 0), divergence (publisher under-claims), and pipeline_run dimension (per-run pricing path).
- Total scorer test count: 83 passed (was 77 in v0.3.1).

### New taxonomy leaf: `tool.code.orchestration`

- For agentic IDEs / multi-phase plan-then-execute flows (Devin, Cursor agent mode, Akkhar-Code, etc.).
- Distinct from `ai.code.completion` (inline suggestion) and `tool.devops.ci` (build runners). The plan-then-execute orchestrator is its own category.
- Added to `schema/asm-v0.3.schema.json` taxonomy `examples` list and `tools/asm-gen/asm_gen.py` keyword allowlist.

### Patches to `schema/asm-v0.3.schema.json`

- New `payment.receipt_envelope_version` field (string; publishers and consumers advertise the envelope version they support).
- New `payment.delegates_to_supported` flag (boolean; opt-in for sub-service attribution).
- Backward compatible: all 75 prior manifests continue to validate. No breaking changes.

### First external reference integration: Akkhar-Code (Akkhar-Labs)

- Spec preserved at `docs/integrations/akkhar-code-receipt-spec.md`.
- Reference receipt example at `examples/receipts/akkhar-code-receipt.json`, validates against the new envelope schema.
- README's new "Reference Integrations" section lists Akkhar-Code as the first external partner with full link set.
- Manifest for `tool.code.orchestration` reserved for Akkhar-Labs but **not yet submitted** — the partner explicitly chose to defer until their production data is real rather than ship a manifest with placeholder numbers. This is the right behaviour for the protocol (see paper §6.5b on data-quality failure modes); the reservation stands without a clock.

### Paper §6.5c (new subsection)

Documents the integration end-to-end: process (72 hours from first contact to merged spec extension), what it validates (schema compatibility surface, governance loop, Trust Delta upstream), what it does **not** validate (n=1 partner, pre-launch product), and full reproducibility paths. Abstract, §7.4, §8, and reference [16] updated to match.

## Schema contributors

The following v0.1 schema features carry external authorship:

| Feature | Contributor | Origin |
|---|---|---|
| `supersedes` correction convention | Rahat Hasan, Akkhar-Labs | RFC issue #7 Q3 reply |
| `public_key_fingerprint` (Ed25519 key pinning) | Rahat Hasan, Akkhar-Labs | RFC issue #7 Q1 reply |
| `cost_delta` as aggregate (not per-dimension) | Rahat Hasan, Akkhar-Labs | RFC issue #7 §2.4 note |
| `tool.code.orchestration` taxonomy leaf | Rahat Hasan, Akkhar-Labs | Initial integration brief 2026-05-16 |

## What's deferred to v0.4

- **Live production receipts** from at least one external publisher endpoint. Akkhar-Labs reserved but deferred to their production timeline (Akkhar-Code is currently their side project; Truck Pai is their main launch).
- **Second reference integration** outside `tool.code.orchestration` to stress-test the receipt envelope (TTS or image-generation natural candidates).
- **Pluggable signature algorithms** (currently Ed25519-only).
- **Schema-enforced receipt size limits** (currently advisory: 64 KB / receipt, 1 MB / envelope).
- **Multi-model seal chaining** (currently pipeline-level seal sufficient; full attribution opt-in via `delegates_to` later).

## Reproducibility

The full release-tagged commit re-derives every offline number in the paper:

```bash
git checkout v0.3.2
pip install -r requirements.txt
python -m pytest scorer/test_scorer.py scorer/test_manifests_schema.py -q  # 83 passed
python -c "import json,jsonschema; \
  s=json.load(open('schema/asm-receipt-envelope-v0.1.schema.json')); \
  e=json.load(open('examples/receipts/akkhar-code-receipt.json')); e.pop('_comment',None); \
  jsonschema.validate(e,s); print('envelope OK')"
make reproduce   # offline experiments only
```

Receipt envelope validation depends on `jsonschema`; everything else is stdlib.

## Citation

```text
Guo, Y. Agent Service Manifest (ASM) v0.3.2. GitHub release, 2026.
https://github.com/YE-YI7/asm-spec/releases/tag/v0.3.2

External schema contributions: Akkhar-Labs (Rahat Hasan) — supersedes
correction convention, public_key_fingerprint Ed25519 key pinning,
cost_delta aggregation, tool.code.orchestration taxonomy leaf.
Tracking: github.com/YE-YI7/asm-spec/issues/7, PR #8.
```

## Numbers at this tag

- 75 manifests across 47 taxonomies (+ `tool.code.orchestration` reserved as 48th).
- 83 scorer tests passing.
- 0/14,519 audited registry entries expose all four core value classes simultaneously.
- 1 external reference integration partner; 0 manifests yet submitted under the new taxonomy (reserved).

## Why v0.3.2 and not v0.3.1

v0.3.1 was tagged 2026-05-08 for the MCP Registry `_meta` work — see `docs/release-v0.3.1.md`. The receipt envelope work in this release is additive on top of that and gets its own minor-version bump. Earlier RFC and PR text said "v0.3.1" by mistake; this has been corrected in `docs/rfcs/trust-delta-receipt-extension-v0.1.md`, `docs/integrations/akkhar-code-receipt-spec.md`, and `paper/asm-paper-draft.md`.
