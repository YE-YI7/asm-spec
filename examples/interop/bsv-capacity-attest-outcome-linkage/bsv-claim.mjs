// BSV rail adapter for content-addressed delivery claims (ASM / capacity-attest).
//
// The content-addressing core is rail-neutral and identical to capacity-attest:
// claimId = sha256 of the canonical JSON of the content fields. Only the
// signature envelope and address encoding are BSV-specific and live HERE:
//   - buyerAddress / sellerAddress are base58 P2PKH addresses (case-sensitive,
//     so NOT lower-cased the way capacity-attest lower-cases 0x hex addresses).
//   - the buyer signs the claimId with a Bitcoin Signed Message (BSM / BRC-77),
//     a recoverable ECDSA signature over a prefixed message, the same secp256k1
//     primitive as EIP-191, different envelope.
//   - the claim carries the payer's compressed pubkey. A BSV P2PKH spend reveals
//     that pubkey on-chain at settlement, so verifying "the buyer signed" is:
//     the signature verifies under buyerPubKey AND P2PKH(buyerPubKey) equals
//     buyerAddress (the address that appears as payer in the settlement tx).
//
// This file deliberately re-implements canonicalize() rather than importing
// capacity-attest, because capacity-attest's schema hard-codes 0x/EIP-191 and
// would reject a base58 address before hashing. The hash ROUTE (sortKeysDeep +
// JSON.stringify + sha256) is byte-for-byte the same; that is the shared core.

import { createHash } from 'node:crypto';
import { PrivateKey, PublicKey, BSM, Utils, Signature } from '@bsv/sdk';

const MAX_DEPTH = 32;

// Deterministic JSON stringify: object keys sorted recursively, arrays kept in
// order. Byte-identical to capacity-attest's canonicalize()/sortKeysDeep().
function sortKeysDeep(value, depth = 0) {
  if (depth > MAX_DEPTH) throw new Error(`nesting exceeds max depth of ${MAX_DEPTH}`);
  if (Array.isArray(value)) return value.map((v) => sortKeysDeep(v, depth + 1));
  if (value !== null && typeof value === 'object') {
    const out = Object.create(null);
    for (const key of Object.keys(value).sort()) out[key] = sortKeysDeep(value[key], depth + 1);
    return out;
  }
  return value;
}
export function canonicalize(value) {
  return JSON.stringify(sortKeysDeep(value, 0));
}

// The content fields that get hashed and signed (everything except claimId and
// signature). Kept explicit so the preimage can never accidentally include a
// derived field.
// buyerPubKey is NOT hashed: like the signature and claimId, it is a verification
// credential carried alongside the content, not content itself. buyerAddress is
// the hashed identity (capacity-attest hashes buyerAddress the same way); the
// pubkey is checked against it at verify time.
const CONTENT_FIELDS = [
  'network', 'sellerAddress', 'buyerAddress', 'assetType',
  'promisedSpec', 'delivered', 'evidenceHash', 'settlementRef', 'timestamp',
];
// A well-formed claim is EXACTLY the content fields plus these three credential
// fields. Anything else is rejected (like capacity-attest's strictObject), so
// the signature effectively covers the whole object: no unsigned field can ride
// along and be trusted by a downstream consumer.
const ALLOWED_KEYS = new Set([...CONTENT_FIELDS, 'claimId', 'signature', 'buyerPubKey']);
function pickContent(claim) {
  const c = {};
  for (const k of CONTENT_FIELDS) if (claim[k] !== undefined) c[k] = claim[k];
  return c;
}

// claimId = '0x' + sha256(canonicalize(content)), the 0x prefix matches the
// cross-rail claimId convention used by the Base fixture.
export function computeClaimId(content) {
  const hash = createHash('sha256').update(canonicalize(pickContent(content)), 'utf8').digest('hex');
  return `0x${hash}`;
}

// Sign a claim's content as the buyer. Returns { claimId, signature, buyerPubKey }.
// `priv` is a @bsv/sdk PrivateKey, supplied by the caller on THEIR machine; this
// module never generates or persists keys.
export function signClaim(priv, content) {
  const claimId = computeClaimId(content);
  const sig = BSM.sign(Utils.toArray(claimId, 'utf8'), priv, 'raw');
  return {
    claimId,
    signature: Utils.toHex(sig.toDER()),
    buyerPubKey: priv.toPublicKey().toString(),
  };
}

// Verify a BSV delivery claim is internally consistent:
//   1. claimId is the sha256 content-address of the claim's own content fields;
//   2. buyerPubKey hashes to buyerAddress (P2PKH);
//   3. the signature verifies under buyerPubKey over the claimId.
// Settlement linkage (the buyerAddress paid sellerAddress in settlementRef on
// chain) is a SEPARATE, network check, see verifySettlement notes in the test.
export function verifyClaim(claim) {
  if (claim === null || typeof claim !== 'object') {
    return { ok: false, reason: 'not_an_object' };
  }
  // Strict shape: reject any key outside the content + credential set, so an
  // unsigned field can never ride along inside a claim that still verifies.
  for (const k of Object.keys(claim)) {
    if (!ALLOWED_KEYS.has(k)) return { ok: false, reason: `unknown_field:${k}` };
  }
  const expected = computeClaimId(claim);
  if (expected.toLowerCase() !== String(claim.claimId).toLowerCase()) {
    return { ok: false, reason: 'claimId_mismatch' };
  }
  let pub;
  try {
    pub = PublicKey.fromString(claim.buyerPubKey);
  } catch (e) {
    return { ok: false, reason: `bad_buyerPubKey: ${e.message}` };
  }
  if (pub.toAddress() !== claim.buyerAddress) {
    return { ok: false, reason: 'pubkey_does_not_match_buyerAddress' };
  }
  let sig;
  try {
    sig = Signature.fromDER(Utils.toArray(claim.signature, 'hex'));
  } catch (e) {
    return { ok: false, reason: `bad_signature_encoding: ${e.message}` };
  }
  let verified;
  try {
    verified = BSM.verify(Utils.toArray(claim.claimId, 'utf8'), sig, pub);
  } catch (e) {
    return { ok: false, reason: `signature_recovery_failed: ${e.message}` };
  }
  if (!verified) return { ok: false, reason: 'signature_does_not_match_buyer' };
  return { ok: true };
}

export { PrivateKey };
