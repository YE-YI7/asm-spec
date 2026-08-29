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

Emitted only by the frozen compatibility profile
(`select(..., selection_profile="legacy-0.5.2", receipt=True)`, or the
equivalent fields on `POST /select`). The closed, versioned machine contract is
[`schema/selection-receipt-v0.1.schema.json`](../../schema/selection-receipt-v0.1.schema.json).
A generated compatibility example is
[`examples/receipts/selection-receipt.json`](../../examples/receipts/selection-receipt.json).

Compatibility boundary: v0.1 requires a scalar `monthly_cost_usd` and cannot
represent workload, free-tier allowance uncertainty, or an unknown total. The
current selector response therefore carries the authoritative structured
`cost_estimate` and does not emit v0.1. The compatibility profile keeps its
historical scalar projection so existing fixtures and consumers remain
byte-compatible. Do not present that legacy projection as a v0.6 cost-safe
decision. A future receipt revision must carry the estimate status, workload,
assumptions, fallback policy, and unknown dimensions rather than silently
changing v0.1.

The frozen receipt identifies its historical selector as
`asm-protocol/0.5.1`. That value is part of the v0.1 fixture contract; it is not
the installed SDK version. The `legacy-0.5.2` profile name identifies the last
SDK compatibility baseline that reproduces this contract.

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

The selected-service invocation fields `interface`, `reach`,
`agent_completable_setup`, and `setup_requires` may be `null` when the consulted
manifest does not declare that fact. `null` means unknown or undeclared; it must
not be interpreted as a negative capability claim.

### The evidence digest

Manifests are mutable — prices change, terms change. `manifest_digest` is a canonical sha256 (`json.dumps(manifest, sort_keys=True, separators=(",",":"))`, UTF-8) that pins the exact evidence state the decision saw. If a provider later edits `data_governance.trains_on_user_data`, the receipt still proves what the field said when the agent chose — the property disputes actually turn on.

## Honest scope

- v0.1 receipts are **unsigned** — they are an honest record from the selector's perspective, not a cryptographic proof against a malicious selector. A `seal` construction consistent with the execution-receipt family is the natural v0.2 once anyone needs it.
- The digest pins the manifest *as consulted*; it does not attest the manifest's claims were *true*. Truth-of-claims is the verification layer's job (`provenance`, `verification` blocks).
- No adoption claim: this is a shipped mechanism with a generated example, not an ecosystem convention. Filed here so settlement-side designs (AP2 mandates, x402 extensions) have a concrete upstream artifact to point at if they want one.
- When a RunnerBinding refers to this receipt, its receipt digest uses the digest profile named by that binding. The guarded-HCL interoperability fixture uses RFC 8785 JCS + SHA-256; that is distinct from the historical Python sorted-JSON construction used for each `manifest_digest` inside the receipt.
