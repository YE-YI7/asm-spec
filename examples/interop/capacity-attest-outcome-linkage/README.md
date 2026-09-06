# capacity-attest → ASM Outcome linkage fixture

This fixture verifies one real external payer attestation and documents how a
future ASM execution record can reference it. It does **not** claim ASM was used
for the original paid call, and it is not evidence of ASM adoption.

The external producer is
[`capacity-attest`](https://github.com/holistis/tokenizen/tree/main/packages/capacity-attest),
maintained by `holistis`. The raw claim stays in that repository and is pinned
to the commit that recorded it. ASM stores only a stable reference, expected
identifiers, a verifier profile, settlement facts, and verification boundaries.

The correct order is:

```text
DecisionReceipt (pre-call selection)
  → OutcomeReceipt (observed execution)
    → external attestation reference (post-call evidence)
```

A DecisionReceipt must not point directly to a claim that did not exist until
after execution. This fixture is an interoperability mapping, not a fabricated
historical DecisionReceipt or OutcomeReceipt.

## Reproduce

```bash
npm ci
npm test
```

For a network-independent claim fetch while still checking the pinned bytes:

```bash
CLAIM_FILE=/path/to/claims.jsonl npm test
```

The settlement test still reads Base Mainnet through the public Base RPC. It
checks transaction success and the USDC `Transfer` event's contract, payer,
payee, and raw amount.

## Proven and not proven

The test reproduces content addressing, EIP-191 payer-signature verification,
and the Base USDC settlement link. It does not prove the buyer's
`delivered=yes` statement, reveal the `evidenceHash` preimage, establish task
correctness, or show that ASM participated in the original call.

OutcomeReceipt v0.1-draft currently has no typed field for non-fiat settlement
assets or external attestations. The mapping records that limitation instead of
mislabeling USDC as fiat USD or silently changing either protocol core.
