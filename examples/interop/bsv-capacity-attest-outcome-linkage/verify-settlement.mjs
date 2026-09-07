// Settlement-linkage check for a BSV delivery claim, the third of the three
// checks (recover-to-buyer, recompute-claimId, confirm-on-chain-transfer). This
// is the BSV analog of reading a USDC Transfer log: fetch the settlement tx and
// confirm (a) an output pays the seller (P2PKH to sellerAddress) and (b) at
// least one input SPENDS A UTXO THAT WAS LOCKED TO buyerAddress, proven by
// fetching the referenced previous output and checking its locking script is
// P2PKH(buyerAddress). Inspecting the prevout (not just the unlocking script's
// revealed pubkey) is what establishes the spent coin belonged to the buyer.
// Read-only; needs no key. Network: WhatsOnChain mainnet.

import { Transaction, P2PKH } from '@bsv/sdk';
import { pathToFileURL } from 'node:url';

const WOC = 'https://api.whatsonchain.com/v1/bsv/main';

// WhatsOnChain rate-limits; retry a few times on 429 with linear backoff so a
// reproduction run does not fail on a transient limit rather than a real fault.
async function wocFetch(path, { tries = 4 } = {}) {
  let last;
  for (let i = 0; i < tries; i++) {
    const r = await fetch(`${WOC}${path}`);
    if (r.ok) return r;
    last = r;
    if (r.status === 429) { await new Promise((res) => setTimeout(res, 1500 * (i + 1))); continue; }
    throw new Error(`WhatsOnChain ${r.status} for ${path}`);
  }
  throw new Error(`WhatsOnChain ${last?.status ?? 'error'} for ${path} after ${tries} tries`);
}

async function fetchTxHex(txid) {
  const r = await wocFetch(`/tx/${txid}/hex`);
  return (await r.text()).trim();
}

// Confirmation depth for the settlement tx, so a mere mempool transaction is not
// accepted as a settled payment. 0 for unconfirmed / not found.
async function fetchConfirmations(txid) {
  const r = await wocFetch(`/tx/hash/${txid}`);
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

// Prove `address` is a payer by inspecting the PREVIOUS OUTPUTS the tx spends:
// for each input, fetch the referenced prevout and check its locking script is
// P2PKH(address). Returns { inputs, sats } over inputs whose prevout was locked
// to `address`. This is stronger than reading the unlocking script's pubkey push,
// which by itself does not prove the spent coin was the buyer's.
async function buyerFundedInputs(tx, address) {
  const target = new P2PKH().lock(address).toHex();
  let inputs = 0;
  let sats = 0;
  for (const i of tx.inputs) {
    const prev = Transaction.fromHex(await fetchTxHex(i.sourceTXID));
    const out = prev.outputs[i.sourceOutputIndex];
    if (!out) continue;
    try {
      if (out.lockingScript.toHex() === target) { inputs += 1; sats += out.satoshis; }
    } catch { /* non-standard prevout */ }
  }
  return { inputs, sats };
}

export async function verifySettlement({ settlementRef, buyerAddress, sellerAddress, minSats = 1, minConfirmations = 1 }) {
  const tx = Transaction.fromHex(await fetchTxHex(settlementRef));
  const sellerPaidSats = satsPaidTo(tx, sellerAddress);
  const buyer = await buyerFundedInputs(tx, buyerAddress);
  const confirmations = await fetchConfirmations(settlementRef);
  const buyerIsPayer = buyer.inputs > 0;
  const ok = sellerPaidSats >= minSats && buyerIsPayer && confirmations >= minConfirmations;
  return {
    ok,
    txid: settlementRef,
    sellerPaidSats,
    buyerIsPayer,
    buyerInputCount: buyer.inputs,
    buyerSpentSats: buyer.sats,
    confirmations,
    sellerAddress,
    buyerAddress,
  };
}

// CLI: node verify-settlement.mjs <txid> <buyerAddress> <sellerAddress>
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [,, settlementRef, buyerAddress, sellerAddress] = process.argv;
  verifySettlement({ settlementRef, buyerAddress, sellerAddress })
    .then((r) => { console.log(JSON.stringify(r, null, 2)); process.exit(r.ok ? 0 : 1); })
    .catch((e) => { console.error('error:', e.message); process.exit(2); });
}
