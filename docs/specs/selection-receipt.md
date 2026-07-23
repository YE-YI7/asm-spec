# Selection Receipt v0.1

**The accountable record of *why this provider*.** An execution receipt (see the [Akkhar-Code integration](../integrations/akkhar-code-receipt-spec.md)) says what a service *did*. A **selection receipt** is its upstream complement: why that service was *chosen* over the alternatives, on what evidence, under which constraints.

## Why it exists

Payment rails are gaining human-not-present autonomy (AP2 v0.2 mandates, x402 sessions). A mandate proves a payment was *authorized*; nothing in the stack proves the payee was *justifiably selected*. When an autonomous agent spends money, "why did it pick this vendor" is the question a user, an auditor, or a dispute process asks first. The selection receipt answers it, machine-readably, at decision time:

```
Selection Receipt      why this provider          (ASM — this spec)
      ↓
Payment mandate        this payment was authorized (AP2)
      ↓
Settlement             the payment executed        (x402)
      ↓
Execution Receipt      what the service did        (execution-receipt family)
```

## Shape (v0.1)

Emitted by the selector when asked (`select(..., receipt=True)`, or `"receipt": true` on `POST /select`). A real, generated example: [`examples/receipts/selection-receipt.json`](../../examples/receipts/selection-receipt.json).

| Field | Meaning |
|---|---|
| `receipt_type` / `receipt_version` | `"selection"` / `"0.1"` |
| `selection_id`, `issued_at` | UUID + UTC timestamp of the decision |
| `selector` | Who decided and under what policy — engine version + a human-readable gate/rank policy string |
| `request` | The full selection request: task, taxonomy, agent reach, platform, required functions, approval triggers, setup requirement |
| `evidence` | **The audit teeth.** One entry per manifest consulted: `service_id` + `manifest_digest` (canonical sha256) |
| `selected`, `selection_reason` | The pick and the stated reason |
| `risk_class`, `approval_required`, `side_effects` | The operational policy surfaced *before* invocation |
| `alternatives`, `rejected` | Ranked runners-up, and every excluded candidate with its nameable gate reason |

### The evidence digest

Manifests are mutable — prices change, terms change. `manifest_digest` is a canonical sha256 (`json.dumps(manifest, sort_keys=True, separators=(",",":"))`, UTF-8) that pins the exact evidence state the decision saw. If a provider later edits `data_governance.trains_on_user_data`, the receipt still proves what the field said when the agent chose — the property disputes actually turn on.

## Honest scope

- v0.1 receipts are **unsigned** — they are an honest record from the selector's perspective, not a cryptographic proof against a malicious selector. A `seal` construction consistent with the execution-receipt family is the natural v0.2 once anyone needs it.
- The digest pins the manifest *as consulted*; it does not attest the manifest's claims were *true*. Truth-of-claims is the verification layer's job (`provenance`, `verification` blocks).
- No adoption claim: this is a shipped mechanism with a generated example, not an ecosystem convention. Filed here so settlement-side designs (AP2 mandates, x402 extensions) have a concrete upstream artifact to point at if they want one.
