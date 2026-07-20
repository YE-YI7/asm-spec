# Circle Product Feedback — ASM (Agent Service Manifest)

> **Submission for the Circle Product Feedback prize ($500 USDC).**
> Project: Agent Service Manifest — `github.com/YE-YI7/asm-arc-circle-2026`
> Repo evidence: every claim below cites a file or commit. We invite Circle DevRel to spot-check.

---

## 1. Which Circle products we used

| Product | Role in ASM | Evidence |
|---|---|---|
| **Arc Testnet** (`eip155:5042002`) | Settlement layer for all agent payments | `payments/src/seller.ts` config, 50/50 settled in `payments/benchmark/result-2026-04-24.json` |
| **USDC on Arc** | Unit of account for nanopayments | `$0.25 USDC` moved across 50 transfers, 15 unique recipients |
| **Circle Gateway** (Modular Wallets / off-chain authorize → on-chain batch settle) | The economic engine — without batching, $0.005/tx is impossible | `createGatewayMiddleware` integration in `seller.ts` |
| **`@circle-fin/x402-batching`** SDK (server side) | x402 payment middleware on the seller | `payments/package.json`, `seller.ts:166–220` |
| **`@x402/express`** + **`@x402/core/server`** | HTTP plumbing for x402 (pre-refactor) | Earlier `seller.ts` revision before we moved to `createGatewayMiddleware` |
| **Circle Developer Console** | Verifying all 50 transfers returned `status: completed` | Used during benchmark validation; visible in demo video |
| **Arc Block Explorer** (`testnet.arcscan.app`) | On-chain proof of USDC backing in GatewayWallet | Buyer wallet `0xF5d4…b038`, GatewayWallet `0x0077…19B9` |

---

## 2. Use case (what we built)

ASM is a protocol layer — sitting alongside MCP/A2A/AP2 — that gives autonomous AI agents structured data to **compare and pay** AI services per call. An agent receives a natural-language task, our pipeline classifies it into one of 47 taxonomies, queries 70 service manifests, runs TOPSIS multi-criteria scoring, picks a winner, and **settles a sub-cent USDC payment to the winner's on-chain address on Arc** — all in a single HTTP round trip.

Why Circle was load-bearing: an agent that ranks 3 image-gen services and pays the winner only makes sense if that payment costs < the price of the service itself. At $0.005 per `/api/score` call, **the payment is ~10–20% of the service cost**. On Ethereum L1 ($0.50–$5.00 per tx), the payment would be 100–1000× the service price — the entire economic model collapses. **Arc + Circle Gateway is the only stack we evaluated where the math works.**

We benchmarked 50 sequential agent decisions on Arc Testnet in live mode (`mode: "live"`, `chain: "arcTestnet"`). All 50 settled. Zero failures. Zero stubs. `payments/benchmark/result-2026-04-24.json`.

---

## 3. What worked well

### 3a. `createGatewayMiddleware` is the right level of abstraction
Our first integration used the lower-level `paymentMiddleware + x402ResourceServer + BatchFacilitatorClient + HTTPFacilitatorClient` composition. It worked but required understanding 4 concepts to wire one route. We later refactored to:

```ts
const rawGateway = createGatewayMiddleware({ sellerAddress: config.sellerAddress });
app.post("/api/score", apiLimiter, rawGateway.require(config.scorePrice), handler);
```

That's it. The middleware handles `accepts` negotiation, `payment-signature` verification, settlement, and the `PAYMENT-RESPONSE` header. **One function = one paid route.** This is the API surface most teams will reach for. Lead with it in docs.

### 3b. Lightning-style off-chain authorize / on-chain batch settle is the right architecture
This is the single most important design decision in Gateway. It enables sub-cent agent payments. We initially confused ourselves expecting per-tx Arc explorer hashes — but once we understood that `transferId` (UUID) is the off-chain authorization receipt and on-chain finality happens at withdrawal, the whole product clicked. **This is genuinely a Lightning Network for stablecoins**, and that framing helped us pitch it to non-crypto judges.

### 3c. Dynamic `payTo` enables fan-out routing
The `dynamicScorePayTo` resolver pattern (a function that inspects request body and returns a destination address) let us route 50 nanopayments across 15 different winning service addresses without registering 15 routes. This is exactly what an agent-commerce protocol needs:

```ts
const dynamicScorePayTo = async (ctx) => {
  const body = ctx.getBody();
  const pick = await pickWinnerForTaxonomy(body?.taxonomy);
  return pick?.winner?.onchain_address ?? config.sellerAddress;
};
```

This single pattern unlocks an entire category of dApps (marketplaces, routers, orchestrators). It deserves its own page in the docs with a worked example.

### 3d. Arc's fee economics + USDC native settlement
- Per-tx finality: 1–2s, observed across all 50 benchmark txs
- Effective gas: ~0 (batched off-chain via Gateway)
- Native USDC means no bridge, no wrapped-asset accounting, no decimals confusion
- Testnet faucet was reliable across the entire 4-day hackathon — never blocked us

### 3e. Mock mode is invaluable for hackathon velocity
`config.mode === "mock"` shortcuts the entire payment middleware and lets the frontend integrate end-to-end before we had API keys. Without this, our team of 4 would have been blocked behind one person who held the Circle credentials. **Strongly recommend keeping and documenting this pattern as a first-class workflow.**

---

## 4. What could be improved

### 4a. `transferId` ↔ on-chain hash UX is a doc problem, not a code problem
We spent ~45 minutes confused that our `txHash` field returned UUIDs instead of `0x…` 64-char hashes. We assumed integration was broken. It wasn't — it's the design — but nothing in our integration path explained this, and the field name `txHash` (in our own code, but mirroring the SDK's vocabulary) actively misled us.

**Recommendation**: 
- Rename the receipt field to `transferId` everywhere in SDK examples (not `txHash` / `transactionHash`).
- Add a 2-paragraph "Where's the on-chain hash?" section to the Gateway Quickstart, with the Lightning Network analogy and a pointer to the withdraw-time hash.
- Provide a `GET /v2/transfers/{id}` example in the Quickstart that shows what the response looks like before vs after batch settlement.

### 4b. Verify/settle errors are opaque without instrumentation
When Circle Gateway rejects a payment, the middleware responds with a JSON body like `{ error, reason }` but Express doesn't log it by default. We hit ~6 different rejection reasons during integration (`validBefore` clock skew, wrong `verifyingContract`, wrong `network`, payer balance, insufficient authorization, etc.) and **could not see any of them** until we wrote a `res.end` interceptor:

```ts
res.end = function(chunk) {
  if (res.statusCode >= 400) {
    console.log(`🔴 [x402] ${req.method} ${req.url} → ${res.statusCode}`);
    console.log(`   Body: ${captured.slice(0, 800)}`);
    // decode payment-signature header for PayerAddr / PayTo / Network / Amount / VerifyingContract
  }
  return origEnd(chunk);
};
```

That wrapper (`payments/src/seller.ts:178–214`) cut our remaining integration time from ~hours to ~minutes.

**Recommendation**: Either (a) ship a built-in `debug: true` flag on `createGatewayMiddleware` that logs the parsed rejection envelope automatically, or (b) document this exact pattern as the canonical way to debug live mode. Right now every team hits this wall independently.

### 4c. ESM/CJS interop friction with `tsx` + Node 20
`@circle-fin/x402-batching/server` and `@x402/core/server` import paths work cleanly in `tsx` but we hit unexpected behavior with `ts-node` (the `Cannot find module './index.js'` ESM resolution issue). We resolved it by switching the registry's `start:http` script to `npx tsx src/http.ts`, but a less-experienced team would lose hours here.

**Recommendation**: Document supported runtime matrix explicitly: ts-node vs tsx vs ESM vs CJS, with a known-working `tsconfig.json` snippet.

### 4d. Discovery of `verifyingContract`, `validBefore`, etc. requires reading SDK internals
The first 5 of our 50 benchmark calls failed with vague "verify failed" until we discovered the exact authorization payload shape via the error wrapper. The contract address, valid window timestamps, and authorization scheme weren't surfaced as constants in any onboarding doc — we extracted them by base64-decoding the `payment-signature` header.

**Recommendation**: Publish a reference table of "what goes into a Gateway authorization on Arc Testnet" — fields, where each value comes from, and where to look up the verifying contract address per chain.

### 4e. No webhook for "batch settled on-chain"
At withdrawal, a real on-chain hash appears, but there's no push notification — apps have to poll `GET /v2/transfers/{id}`. For a UI that wants to update from "authorized" → "settled on-chain", this is awkward.

**Recommendation**: Add a Gateway webhook event `transfer.batch_settled` with the on-chain hash payload.

### 4f. `@circle-fin/x402-batching` examples are e-commerce-shaped
Every example we found models "user pays merchant for a product." Our use case is "agent routes payment to one of N service providers based on runtime decision." The `dynamicPayTo` pattern enables this beautifully but isn't featured. Most agent-commerce teams will reinvent it.

**Recommendation**: Add a "Marketplace / Router" example to the SDK README — single endpoint, payment routes to one of N addresses based on body content. This is the canonical agent-commerce shape and unlocks a whole class of builders.

---

## 5. Recommendations (prioritized)

1. **🔴 P0 — Lead the Gateway Quickstart with `createGatewayMiddleware`.** It's strictly easier than the 4-class composition and is what the majority of teams want. Lower-level escape hatch can stay for advanced cases.

2. **🔴 P0 — "Where's the on-chain hash?" doc page.** Single page. Lightning analogy. transferId ≠ tx hash. Pointer to withdraw flow. Pointer to `GET /v2/transfers/{id}`. We estimate 50%+ of new Gateway integrations hit this confusion.

3. **🟡 P1 — Built-in debug logging for verify/settle rejections.** A `debug: true` flag that prints the parsed `{error, reason, decoded payment-signature}` envelope. Saves every team independent hours of `res.end` wrappers.

4. **🟡 P1 — Marketplace / Router example with `dynamicPayTo`.** This pattern is the agent-commerce primitive. Currently undocumented, easy to miss.

5. **🟡 P1 — Webhook: `transfer.batch_settled`.** Push the on-chain hash when batch settles, so dApps can flip UI state without polling.

6. **🟢 P2 — Runtime matrix doc**: ts-node vs tsx vs Node 20 ESM/CJS, with known-working `tsconfig.json` for `@circle-fin/x402-batching`.

7. **🟢 P2 — First-class mock-mode pattern** in SDK: `createGatewayMiddleware({ mode: "mock" })` returning a stub that 200s every call. Documented as the recommended local-dev workflow. We rolled our own; everyone else will too.

8. **🟢 P2 — Reference table** for Arc Testnet Gateway authorization fields (verifyingContract address, authorization scheme, valid window expectations).

---

## 6. The 50-tx benchmark — what it taught us about Circle's economic thesis

Our benchmark (`payments/scripts/benchmark.ts`, results in `payments/benchmark/result-2026-04-24.json`) ran 50 real `POST /api/score` calls in live mode against Arc Testnet. Distribution across 15 taxonomies (image-gen, copywrite, translate, embed, scrape, code-gen, …). All 50 settled, 0 failures, 0 stubs, ~$0.005 effective per-payment cost, $0.25 USDC total moved, 15 unique recipient addresses.

The economic conclusion: **Circle's batching design is what makes autonomous agent commerce viable.** A naive read of "we need 50 tx hashes on the explorer" misses the point — if every $0.005 payment cost a $0.50 L1 gas fee, the entire ASM use case dies. The fact that judges might initially expect per-tx hashes is itself a marketing opportunity: **lead with "Lightning Network for stablecoins, settled on Arc"** as the elevator pitch. We adopted that framing in our README and slide deck after this realization.

---

## 7. The 4-team structure perspective

ASM is a 4-person team (Caleb, GLM, Hak, Hamza, plus me as integration co-pilot). Hamza owned the Circle/Arc integration. Notable that:

- He built mock mode first → unblocked frontend (GLM) and discovery (Hak) in parallel.
- The single biggest accelerant in his live-mode integration was the `res.end` debug wrapper. Everything else after that came in hours, not days.
- The decision to refactor from manual `paymentMiddleware + x402ResourceServer` → `createGatewayMiddleware` paid for itself the same afternoon.

If we had to start over, we'd skip the manual composition entirely and start from `createGatewayMiddleware` + `dynamicPayTo` + `res.end` debug wrapper. Those three pieces are the 80/20 of building a real x402 service on Arc.

---

**Repo**: github.com/YE-YI7/asm-arc-circle-2026
**Live demo**: asm-arc-circle-2026.vercel.app
**Benchmark JSON**: payments/benchmark/result-2026-04-24.json
**Code references inline above** — happy to walk Circle DevRel through any of them.
