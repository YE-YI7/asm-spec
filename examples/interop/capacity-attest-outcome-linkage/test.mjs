import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { verifyClaim } from "capacity-attest/dist/signing.js";

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

async function rpc(method, params) {
  const response = await fetch("https://mainnet.base.org", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    signal: AbortSignal.timeout(15_000),
  });
  assert.equal(response.ok, true, `Base RPC failed with HTTP ${response.status}`);
  const payload = await response.json();
  assert.equal(payload.error, undefined, JSON.stringify(payload.error));
  return payload.result;
}

test("pinned capacity-attest claim verifies and tampering fails", async () => {
  const raw = await claimBytes();
  const digest = `sha256:${createHash("sha256").update(raw).digest("hex")}`;
  assert.equal(digest, fixture.external_attestation.raw_claim_sha256);

  const claim = JSON.parse(raw.toString("utf8").trim());
  assert.equal(claim.claimId, fixture.external_attestation.claim_id);
  assert.equal(claim.buyerAddress, fixture.external_attestation.expected_signer);
  assert.deepEqual(verifyClaim(claim), { ok: true });
  assert.deepEqual(verifyClaim({ ...claim, delivered: "no" }), {
    ok: false,
    reason: "claimId_mismatch",
  });
  assert.deepEqual(verifyClaim({ ...claim, buyerAddress: claim.sellerAddress }), {
    ok: false,
    reason: "claimId_mismatch",
  });
});

test("Base receipt binds the declared USDC transfer", async () => {
  const receipt = await rpc("eth_getTransactionReceipt", [
    fixture.settlement.transaction_hash,
  ]);
  assert.equal(receipt.status, "0x1");

  const transferTopic =
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
  const addressTopic = (address) => `0x${address.toLowerCase().slice(2).padStart(64, "0")}`;
  const amountData = `0x${BigInt(fixture.settlement.raw_amount).toString(16).padStart(64, "0")}`;
  const matchingLog = receipt.logs.find(
    (log) =>
      log.address.toLowerCase() === fixture.settlement.asset_contract &&
      log.topics[0] === transferTopic &&
      log.topics[1] === addressTopic(fixture.settlement.payer) &&
      log.topics[2] === addressTopic(fixture.settlement.payee) &&
      log.data === amountData,
  );
  assert.ok(matchingLog, "expected USDC Transfer log was not found");
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
