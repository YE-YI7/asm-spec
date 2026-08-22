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

Emitted by the selector when asked (`select(..., receipt=True)`, or `"receipt": true` on `POST /select`). The closed, versioned machine contract is [`schema/selection-receipt-v0.1.schema.json`](../../schema/selection-receipt-v0.1.schema.json). A checked-in v0.1 fixture is [`examples/interop/deepseek-harness-selection-boundary/selection-receipt.json`](../../examples/interop/deepseek-harness-selection-boundary/selection-receipt.json).

This v0.1 contract is frozen because external fixtures pin its URI and byte digest. New producers should use [Selection Receipt v0.2](selection-receipt-v0.2.md), which makes the unsigned envelope and digest profile explicit without silently changing v0.1.

| Field | Meaning |
|---|---|
| `receipt_type` / `receipt_version` | `"selection"` / `"0.1"` |
| `selection_id`, `issued_at` | UUID + UTC timestamp of the decision |
| `selector` | Claimed producer and policy — engine version + a human-readable gate/rank policy string |
| `request` | The full selection request: task, taxonomy, agent reach, platform, required functions, approval triggers, setup requirement |
| `evidence` | **The audit teeth.** One entry per manifest consulted: `service_id` + `manifest_digest` |
| `selected`, `selection_reason` | The pick and the stated reason |
| `risk_class`, `approval_required`, `side_effects` | The operational policy surfaced *before* invocation |
| `alternatives`, `rejected` | Ranked runners-up, and every excluded candidate with its nameable gate reason |

The selected-service invocation fields `interface`, `reach`,
`agent_completable_setup`, and `setup_requires` may be `null` when the consulted
manifest does not declare that fact. `null` means unknown or undeclared; it must
not be interpreted as a negative capability claim.

### The evidence digest

Manifests are mutable — prices change, terms change. `manifest_digest` pins the exact evidence state the decision saw. If a provider later edits `data_governance.trains_on_user_data`, the receipt still records what the field said when the agent chose.

## Honest scope

- v0.1 receipts are **unsigned** — they are an honest record from the selector's perspective, not a cryptographic proof against a malicious selector. The `selector.name` value is a claimed producer label, not a verified issuer.
- The digest pins the manifest *as consulted*; it does not attest the manifest's claims were *true*. Truth-of-claims is the verification layer's job (`provenance`, `verification` blocks).
- `approval_required` is a pre-call policy result. It is not evidence that a person or mandate authorized an invocation or payment.
- `request.task` and other request fields may contain sensitive user intent. Evidence systems should reference a receipt by digest and status rather than copy or upload the raw receipt without an explicit privacy policy and consent.
- No adoption claim: this is a shipped mechanism with a generated example, not an ecosystem convention. Filed here so settlement-side designs (AP2 mandates, x402 extensions) have a concrete upstream artifact to point at if they want one.
- When a RunnerBinding refers to this receipt, its receipt digest uses the digest profile named by that binding. The guarded-HCL interoperability fixture uses RFC 8785 JCS + SHA-256; that is distinct from the historical Python sorted-JSON construction used for each `manifest_digest` inside the receipt.
