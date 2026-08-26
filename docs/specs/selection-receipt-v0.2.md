# Selection Receipt v0.2

**The explicitly unsigned, digest-profiled record of why a provider was selected.** This revision preserves the v0.1 decision model while making the receipt envelope's verification status and each manifest digest construction machine-readable.

The closed machine contract is [`schema/selection-receipt-v0.2.schema.json`](../../schema/selection-receipt-v0.2.schema.json). A generated example is [`examples/receipts/selection-receipt.json`](../../examples/receipts/selection-receipt.json).

## Why v0.2 exists

Selection Receipt v0.1 is frozen because external interoperability fixtures pin its schema URI and byte digest. Adding required fields to that schema would make already-issued v0.1 receipts invalid without changing their declared version.

v0.2 therefore adds, without reinterpreting v0.1:

- top-level `verification_status: "unsigned"`, which describes the receipt envelope and does not verify `selector.name` as an issuer;
- `hash_algorithm: "sha256"` on each evidence item;
- `canonicalization: "asm-json-sort-keys-v1"` on each evidence item.

## Evidence digest profile

`asm-json-sort-keys-v1` uses UTF-8 JSON with recursively sorted object keys, preserved array order, no insignificant whitespace, `ensure_ascii=False`, and Python standard-library primitive serialization. It is deliberately versioned and is **not** RFC 8785 JCS: number and property-order edge cases differ. Moving to JCS requires a new canonicalization label rather than a silent change to existing digests.

## Honest scope

- `verification_status: "unsigned"` is not cryptographic attestation. `selector.name` remains a claimed producer label.
- `manifest_digest` pins the descriptor consulted; it does not establish that its pricing, SLA, quality, or other claims were true.
- `approval_required` is a pre-call policy result, not evidence that a person or mandate authorized an invocation or payment.
- Request fields can contain sensitive user intent. Evidence systems should reference the receipt by digest and status rather than copy or upload it without an explicit privacy policy and consent.
- The receipt records selection only. It does not prove execution, payment, authorization, partnership, or adoption.

`asm-protocol` 0.5.3 is the first planned package release to emit v0.2. Public 0.5.2 emits v0.1 and remains valid against the frozen v0.1 schema.
