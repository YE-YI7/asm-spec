// Settlement-linkage check for a BSV delivery claim, the third of the three
// checks (recover-to-buyer, recompute-claimId, confirm-on-chain-transfer). This
// is the BSV analog of reading a USDC Transfer log: fetch the settlement tx and
// confirm an output pays the seller (P2PKH to sellerAddress) and an input is
// spent by the buyer (a P2PKH-spend input whose revealed pubkey hashes to
// buyerAddress). Read-only; needs no key. Network: WhatsOnChain mainnet.

import { Transaction, PublicKey, P2PKH } from '@bsv/sdk';
import { pathToFileURL } from 'node:url';

const WOC = 'https://api.whatsonchain.com/v1/bsv/main';

async function fetchTxHex(txid) {
  const r = await fetch(`${WOC}/tx/${txid}/hex`);
  if (!r.ok) throw new Error(`WhatsOnChain ${r.status} for tx ${txid}`);
  return (await r.text()).trim();
}

// Confirmation depth for the settlement tx, so a mere mempool transaction is not
// accepted as a settled payment. 0 for unconfirmed / not found.
async function fetchConfirmations(txid) {
  const r = await fetch(`${WOC}/tx/hash/${txid}`);
  if (!r.ok) throw new Error(`WhatsOnChain ${r.status} for tx ${txid}`);
  const j = await r.json();
  return Number(j.confirmations) || 0;
}

// Return the satoshis paid to `address` across all P2PKH outputs of `tx`.
function satsPaidTo(tx, address) {
  const target = new P2PKH().lock(address).toHex();
  let sats = 0;
  for (const o of tx.outputs) {
    try { if (o.lockingScript.toHex() === target) sats += o.satoshis; } catch { /* non-standard */ }
  }
  return sats;
}

// Is `address` a payer? A P2PKH-spend input's unlocking script is <sig> <pubkey>;
// the pubkey's P2PKH address is the spender. We check any input reveals a pubkey
// hashing to `address`.
function isPayer(tx, address) {
  for (const i of tx.inputs) {
    const us = i.unlockingScript;
    if (!us || !us.chunks || us.chunks.length < 2) continue;
    const last = us.chunks[us.chunks.length - 1];
    if (!last || !last.data) continue;
    try {
      const hex = last.data.map((b) => b.toString(16).padStart(2, '0')).join('');
      if (PublicKey.fromString(hex).toAddress() === address) return true;
    } catch { /* not a pubkey push */ }
  }
  return false;
}

export async function verifySettlement({ settlementRef, buyerAddress, sellerAddress, minSats = 1, minConfirmations = 1 }) {
  const tx = Transaction.fromHex(await fetchTxHex(settlementRef));
  const sellerPaidSats = satsPaidTo(tx, sellerAddress);
  const buyerIsPayer = isPayer(tx, buyerAddress);
  const confirmations = await fetchConfirmations(settlementRef);
  const ok = sellerPaidSats >= minSats && buyerIsPayer && confirmations >= minConfirmations;
  return { ok, txid: settlementRef, sellerPaidSats, buyerIsPayer, confirmations, sellerAddress, buyerAddress };
}

// CLI: node verify-settlement.mjs <txid> <buyerAddress> <sellerAddress>
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [,, settlementRef, buyerAddress, sellerAddress] = process.argv;
  verifySettlement({ settlementRef, buyerAddress, sellerAddress })
    .then((r) => { console.log(JSON.stringify(r, null, 2)); process.exit(r.ok ? 0 : 1); })
    .catch((e) => { console.error('error:', e.message); process.exit(2); });
}
