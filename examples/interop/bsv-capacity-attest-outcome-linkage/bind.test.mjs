// Offline demonstration of the normative "Verifier requirements" (README).
// Runs with zero network: it uses only the pinned claim on disk, the vendored
// content-address + signature-recovery verifier, and the reference bind. No
// WhatsOnChain read. `node --test` picks it up automatically.
//
// The point it makes concrete: content addressing + signature recovery are
// BEARER checks (they pass for whoever holds the claim), and the claim becomes
// the verifier's OWN only once it is bound to the settlement the verifier paid.
// A different settlement, or no expected settlement at all, must be refused.

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { verifyClaim } from "./bsv-claim.mjs";
import { bindClaim } from "./bind.mjs";

const claim = JSON.parse(
  await readFile(new URL("./claim_inference.json", import.meta.url), "utf8"),
);

// Separately pinned test expectations representing host-owned payment context.
// This is a synthetic consumer context, not evidence of historical ASM use.
const paid = Object.freeze({
  settlementRef: "77030c6192c6e86b808f1d7afa210b874bad86ed6a6b4ef69a8ccebc51ec83c6",
  buyerAddress: "1ErDfgzGWe6kDSHWWZPUSpVRRvfQo7rDdZ",
  sellerAddress: "1LdqUbdZ6GY71KxThU6aKfuKXxgmTn82cv",
});

test("bearer property: the claim's own checks verify for any holder", () => {
  // No payer/verifier identity is involved here: content address + signature
  // recovery hold for a copy of the claim in anyone's hands. That is exactly why
  // a bind is required.
  assert.deepEqual(verifyClaim(claim), { ok: true });
});

test("bound to the settlement the verifier paid: accepted", () => {
  assert.deepEqual(bindClaim(claim, paid), { ok: true });
});

test("bound to a DIFFERENT settlement (replay/transfer): refused", () => {
  const otherTxid = "0".repeat(64);
  assert.equal(bindClaim(claim, { settlementRef: otherTxid }).reason, "settlementRef_not_mine");
});

test("UNBOUND (no expected settlement supplied): refused, not silently passed", () => {
  assert.match(bindClaim(claim, {}).reason, /^unbound/);
  assert.match(bindClaim(claim).reason, /^unbound/);
});

test("bound with the wrong payer address (a transferred claim): refused", () => {
  const notMine = { ...paid, buyerAddress: "1SomeoneElseAddressxxxxxxxxxxxxxxx" };
  assert.equal(bindClaim(claim, notMine).reason, "buyerAddress_not_mine");
});

test("signature and binding compose offline; settlement and delivery remain separate", () => {
  const v = verifyClaim(claim);
  assert.equal(v.ok, true);
  const b = bindClaim(claim, paid);
  assert.equal(b.ok, true);
});


test("invalid inputs fail closed without coercion or crashes", () => {
  for (const value of [undefined, null, {}, [], 123, "undefined", "", "a".repeat(63), "g".repeat(64)]) {
    assert.equal(bindClaim(claim, { settlementRef: value }).ok, false);
    assert.equal(bindClaim({ settlementRef: value }, paid).ok, false);
  }
  for (const value of [null, undefined, [], 123]) {
    assert.equal(bindClaim(value, paid).ok, false);
    assert.equal(bindClaim(claim, value).ok, false);
  }
  assert.equal(bindClaim({}, { settlementRef: "undefined" }).ok, false);
  assert.equal(bindClaim({ settlementRef: 123 }, { settlementRef: 123 }).ok, false);
});

test("hex case is equivalent but base58 address case is not", () => {
  assert.equal(bindClaim(claim, { ...paid, settlementRef: paid.settlementRef.toUpperCase() }).ok, true);
  for (const field of ["buyerAddress", "sellerAddress"]) {
    assert.equal(bindClaim(claim, { ...paid, [field]: paid[field].toLowerCase() }).ok, false);
    for (const value of [undefined, null, "", " ", 123]) {
      assert.equal(bindClaim(claim, { ...paid, [field]: value }).ok, false);
    }
  }
});

test("matching identifiers alone do not authenticate a tampered claim", () => {
  const tampered = { ...claim, delivered: "no" };
  assert.equal(bindClaim(tampered, paid).ok, true);
  assert.equal(verifyClaim(tampered).ok, false);
});
