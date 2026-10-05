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
P2PKH address encoding, and a **compact Bitcoin Signed Message (BSM)** signature
recovered to that address. capacity-attest's own `verifyClaim` is ETH/EIP-191
typed and rejects a base58 claim before hashing, so the shared piece is the hash
route, not the schema.

This fixture uses the legacy compact BSM signature API. `@bsv/sdk` marks BSM as
deprecated in favor of BRC-77; BSM and BRC-77 are not equivalent, and migrating
the signature envelope to BRC-77 is out of scope for this interoperability
fixture.

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

### Offline mode

The run has a deterministic offline path with no network at all. `CLAIM_FILE`
reads the claim from disk (a copy of the pinned claim ships here as
`claim_inference.json`, still checked against the pinned sha256), and
`FIXTURE_OFFLINE=1` skips the live settlement read:

```bash
CLAIM_FILE=./claim_inference.json FIXTURE_OFFLINE=1 npm test
```

The deterministic integrity, signature, binding, and boundary checks run with
zero network calls. The live settlement test is
the only networked step, so it can be kept out of required CI.

The settlement test reads BSV mainnet through WhatsOnChain (with retry/backoff on
rate limits). It checks that the transaction is confirmed, that a P2PKH output
pays the payee, and that an input **spends a previous output locked to the
payer** (the prevout locking script is `P2PKH(payer)`), the BSV analog of reading
an ERC-20 `Transfer` log.

## Verifier requirements (normative)

A signed, content-addressed attestation can be copied by any holder. Its signature
binds the statement to its signer, but does not establish that the holder paid
for the call. Signature and content-address checks alone prove neither settlement
nor delivery. This fixture leaves delivery and task correctness unproven even
when the separate chain check succeeds.

To rely on a settlement attestation as evidence of its **own** paid call, a
verifier MUST:

1. **Hold the settlement reference independently.** Compare the record's
   `settlementRef` (and, where present, the payer identity) against the
   transaction the verifier itself paid, taken from the verifier's own context,
   never read back out of the record being checked.
2. **Refuse when unbound.** If no expected settlement reference is supplied, the
   verifier MUST refuse rather than pass. An absent binding is a refusal, not a
   skip: silence about which payment this is must not be read as "mine."
3. **Reconcile against the chain.** Read `settlementRef` on the relevant chain and
   confirm the movement it names (payer → payee, amount) actually occurred.

This is the settlement-layer form of the general rule that the **acceptance rule
must remain the verifier's**: adding checks does not establish that a record is the
verifier's own unless the reference those checks run against is one the verifier
holds independently. A reference implementation of the binding for this fixture's
rail is `bindX402Receipt(...)` / `verifySettlement({ ..., expected })` in the
producer repository; the same requirement applies to any rail's attestation.

`bindClaim` checks only equality with independently supplied expectations; it
does not verify a signature, read the chain, validate address checksums, establish
request identity, or prevent reuse of a settlement across multiple calls. A host
must associate its payment with its own request and enforce any single-use rule.
The local vendored `verifySettlement` is unchanged and does not compose this
binding automatically. These requirements apply to this example, not MCP core.

`bind.mjs` + `bind.test.mjs` here demonstrate it offline against the pinned claim
(no network): the claim's own content-address and signature-recovery checks pass
for any holder, binding it to the settlement the verifier paid is accepted, and a
different settlement or an absent expected settlement is refused. Run with
`npm test` (the demo is fully offline; only the live settlement read needs the
network).

## Proven and not proven

The test reproduces content addressing, **compact BSM signature recovery** (the
signer's public key is recovered from the signature and the `claimId`, then
`P2PKH(recovered)` must equal `buyerAddress`; the carried `buyerPubKey` is
cross-checked, not trusted), and the BSV settlement link. It does **not** prove
the buyer's `delivered=yes` statement, reveal the `evidenceHash` preimage,
establish task correctness, or show that ASM participated in the original call.

OutcomeReceipt v0.1-draft currently has no typed field for non-fiat settlement
assets or external attestations. The mapping records that limitation instead of
mislabeling BSV as fiat or silently changing either protocol core.

## Vendored adapter

`bsv-claim.mjs` and `verify-settlement.mjs` are copied verbatim from the pinned
producer commit so this example runs self-contained (only `@bsv/sdk` >= 2 is
installed). The canonical source is the producer repository at the commit named
in `linkage.fixture.json` → `external_attestation.verifier.commit`.
