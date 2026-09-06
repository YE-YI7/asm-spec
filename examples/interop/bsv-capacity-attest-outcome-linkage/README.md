# bsv-capacity-attest → ASM Outcome linkage fixture (BSV rail)

A BSV-settled sibling of the Base/USDC `capacity-attest` linkage fixture. It
verifies one real external payer attestation for a BSV micropayment and
documents how a future ASM execution record can reference it. It does **not**
claim ASM was used for the original paid call, and it is not evidence of ASM
adoption.

The external producer is
[`bsv-capacity-attest`](https://github.com/EmbryoSpace/bsv-capacity-attest)
(EmbryoSpace / BSVKey), a rail adapter that reuses the **same rail-neutral
content-addressing** as
[`capacity-attest`](https://github.com/holistis/tokenizen/tree/main/packages/capacity-attest)
(holistis): `claimId` is the sha256 of the canonical JSON of the claim's content
fields. Only two things are BSV-specific and isolated behind the adapter: base58
P2PKH address encoding, and a **Bitcoin Signed Message (BSM / BRC-77)** signature
recovered to that address. capacity-attest's own `verifyClaim` is ETH/EIP-191
typed and rejects a base58 claim before hashing, so the shared piece is the hash
route, not the schema.

The raw claim stays in the producer repository, pinned to the commit that
recorded it. ASM stores only a stable reference, expected identifiers, a verifier
profile, settlement facts, and verification boundaries.

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
CLAIM_FILE=/path/to/claim_inference.json npm test
```

The settlement test reads BSV mainnet through WhatsOnChain. It checks that the
transaction is confirmed, that a P2PKH output pays the payee, and that an input
is spent by the payer (the BSV analog of reading an ERC-20 `Transfer` log).

## Proven and not proven

The test reproduces content addressing, BSM payer-signature recovery (signature
→ pubkey → base58 `buyerAddress`), and the BSV settlement link. It does **not**
prove the buyer's `delivered=yes` statement, reveal the `evidenceHash` preimage,
establish task correctness, or show that ASM participated in the original call.

OutcomeReceipt v0.1-draft currently has no typed field for non-fiat settlement
assets or external attestations. The mapping records that limitation instead of
mislabeling BSV as fiat or silently changing either protocol core.

## Vendored adapter

`bsv-claim.mjs` and `verify-settlement.mjs` are copied verbatim from the pinned
producer commit so this example runs self-contained (only `@bsv/sdk` is
installed). The canonical source is the producer repository at the commit named
in `linkage.fixture.json` → `external_attestation.verifier.commit`.
