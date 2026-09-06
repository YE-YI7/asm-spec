import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";

// BSV rail adapter (vendored from github.com/EmbryoSpace/bsv-capacity-attest at
// the commit pinned in the fixture's verifier.commit). The canonical source is
// that repo; it is copied here so this example is self-contained. Only external
// dependency is @bsv/sdk.
import { verifyClaim } from "./bsv-claim.mjs";
import { verifySettlement } from "./verify-settlement.mjs";

const fixture = JSON.parse(
  await readFile(new URL("./linkage.fixture.json", import.meta.url), "utf8"),
);

async function claimBytes() {
  if (process.env.CLAIM_FILE) {
    return readFile(process.env.CLAIM_FILE);
  }
  const response = await fetch(fixture.external_attestation.raw_claim_url, {
    signal: AbortSignal.timeout(15_000),
  });
  assert.equal(response.ok, true, `claim fetch failed with HTTP ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

test("pinned BSV claim verifies and tampering fails", async () => {
  const raw = await claimBytes();
  const digest = `sha256:${createHash("sha256").update(raw).digest("hex")}`;
  assert.equal(digest, fixture.external_attestation.raw_claim_sha256);

  const claim = JSON.parse(raw.toString("utf8").trim());
  assert.equal(claim.claimId, fixture.external_attestation.claim_id);
  assert.equal(claim.buyerAddress, fixture.external_attestation.expected_signer);
  assert.deepEqual(verifyClaim(claim), { ok: true });
  // Any content edit breaks the content address.
  assert.deepEqual(verifyClaim({ ...claim, delivered: "no" }), {
    ok: false,
    reason: "claimId_mismatch",
  });
  assert.deepEqual(verifyClaim({ ...claim, buyerAddress: claim.sellerAddress }), {
    ok: false,
    reason: "claimId_mismatch",
  });
});

test("BSV settlement binds the declared transfer (payer -> payee on-chain)", async () => {
  const s = await verifySettlement({
    settlementRef: fixture.settlement.transaction_hash,
    buyerAddress: fixture.settlement.payer,
    sellerAddress: fixture.settlement.payee,
    minSats: Number(fixture.settlement.raw_amount),
  });
  assert.equal(s.ok, true, "expected the settlement tx to pay payee and be spent by payer");
  assert.equal(s.buyerIsPayer, true);
  assert.ok(
    s.sellerPaidSats >= Number(fixture.settlement.raw_amount),
    `payee received ${s.sellerPaidSats} sats, expected >= ${fixture.settlement.raw_amount}`,
  );
});

test("fixture keeps the ASM boundary explicit", () => {
  assert.equal(fixture.historical_asm_use, false);
  assert.equal(
    fixture.asm_mapping.decision_receipt_must_not_reference_post_call_claim,
    true,
  );
  assert.deepEqual(fixture.asm_mapping.chain_order, [
    "DecisionReceipt",
    "OutcomeReceipt",
    "external_attestation_reference",
  ]);
  assert.ok(fixture.not_independently_proven.includes("delivered=yes"));
  assert.ok(fixture.not_independently_proven.includes("evidenceHash preimage"));
});
