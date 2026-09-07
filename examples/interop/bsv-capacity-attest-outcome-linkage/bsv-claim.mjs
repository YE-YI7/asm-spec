// BSV rail adapter for content-addressed delivery claims (ASM / capacity-attest).
//
// The content-addressing core is rail-neutral and identical to capacity-attest:
// claimId = sha256 of the canonical JSON of the content fields. Only the
// signature envelope and address encoding are BSV-specific and live HERE:
//   - buyerAddress / sellerAddress are base58 P2PKH addresses (case-sensitive,
//     so NOT lower-cased the way capacity-attest lower-cases 0x hex addresses).
//   - the buyer signs the claimId with a Bitcoin Signed Message (BSM), a
//     compact, recoverable ECDSA signature over a prefixed message, the same
//     secp256k1 primitive as EIP-191, different envelope.
//   - verification RECOVERS the signer from the signature: the compact BSM
//     signature carries the recovery id, so the public key is derived from the
//     signature and the claimId alone (not read from a supplied field), then
//     P2PKH(recovered pubkey) must equal buyerAddress (the address that appears
//     as payer in the settlement tx). This mirrors the Base fixture's
//     ecrecover-to-signer, with base58 P2PKH in place of a 0x address.
//   - buyerPubKey is still carried for convenience (a BSV P2PKH spend reveals it
//     on chain), but it is NOT trusted: verification cross-checks it against the
//     recovered key rather than relying on it.
//
// This file deliberately re-implements canonicalize() rather than importing
// capacity-attest, because capacity-attest's schema hard-codes 0x/EIP-191 and
// would reject a base58 address before hashing. The hash ROUTE (sortKeysDeep +
// JSON.stringify + sha256) is byte-for-byte the same; that is the shared core.

import { createHash } from 'node:crypto';
import { PrivateKey, PublicKey, BSM, Utils, Signature, BigNumber } from '@bsv/sdk';

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
// module never generates or persists keys. The signature is a compact,
// recoverable BSM signature (base64), so a verifier can recover the signer from
// the signature alone.
export function signClaim(priv, content) {
  const claimId = computeClaimId(content);
  const signature = BSM.sign(Utils.toArray(claimId, 'utf8'), priv, 'base64');
  return {
    claimId,
    signature,
    buyerPubKey: priv.toPublicKey().toString(),
  };
}

// Verify a BSV delivery claim is internally consistent:
//   1. claimId is the sha256 content-address of the claim's own content fields;
//   2. the compact BSM signature RECOVERS a public key from the signature and
//      the claimId, and P2PKH(recovered pubkey) equals buyerAddress;
//   3. if the claim carries buyerPubKey, it must equal the recovered key (it is
//      cross-checked, never trusted as the basis of verification).
// Settlement linkage (the buyerAddress paid sellerAddress in settlementRef on
// chain) is a SEPARATE, network check, see verifySettlement.
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
  // Decode the compact BSM signature (65 bytes: recovery byte + r + s).
  let raw;
  try {
    raw = Utils.toArray(claim.signature, 'base64');
  } catch (e) {
    return { ok: false, reason: `bad_signature_encoding: ${e.message}` };
  }
  if (!Array.isArray(raw) || raw.length !== 65 || raw[0] < 27 || raw[0] >= 35) {
    return { ok: false, reason: 'bad_signature_encoding: not a 65-byte BSM compact signature' };
  }
  const recoveryId = (raw[0] - 27) & 3;
  const msg = Utils.toArray(claim.claimId, 'utf8');
  // Recover the signer's public key from the signature + message alone.
  let recovered;
  try {
    const sig = Signature.fromCompact(claim.signature, 'base64');
    const e = new BigNumber(BSM.magicHash(msg));
    recovered = sig.RecoverPublicKey(recoveryId, e);
    if (!BSM.verify(msg, sig, recovered)) {
      return { ok: false, reason: 'signature_invalid' };
    }
  } catch (e) {
    return { ok: false, reason: `signature_recovery_failed: ${e.message}` };
  }
  // The recovered key must be the buyer (the address that pays on chain).
  if (recovered.toAddress() !== claim.buyerAddress) {
    return { ok: false, reason: 'recovered_address_does_not_match_buyerAddress' };
  }
  // If a buyerPubKey is carried, it is cross-checked, never trusted.
  if (claim.buyerPubKey !== undefined && recovered.toString() !== claim.buyerPubKey) {
    return { ok: false, reason: 'buyerPubKey_does_not_match_recovered' };
  }
  return { ok: true };
}

export { PrivateKey, PublicKey };
