# Lablab Hackathon Submission — Copy Draft

---

## 1. Project Title (≤50 chars)

```
ASM — Agent Service Manifest for Circle × Arc
```

*(42 chars)*

---

## 2. Short Description (50–255 chars)

```
ASM is an open protocol that lets AI agents discover, rank, and pay for AI services per API call at sub-cent precision. Track: Per-API Monetization Engine. 50 USDC tx on Arc via Circle Gateway at $0.005/tx — 100× cheaper than L1 gas.
```

*(249 chars)*

---

## 3. Long Description (≥600 chars, target ~1100)

**"Agents shouldn't shop. They should settle."**

ASM (Agent Service Manifest) is the first open protocol that gives AI agents structured, machine-readable data to **evaluate, compare, and automatically select** AI services — then route a sub-cent USDC payment to the winner via Circle's x402 nanopayment protocol on Arc testnet. All in one HTTP request.

### The Problem

When an autonomous agent needs to call an API — translate text, generate an image, transcribe audio — it faces a choice between multiple providers. Today it has **zero structured data** to make that decision. The result: blind selection (hardcoded API keys), 3–10x cost overrun or quality mismatch, and non-reproducible decisions. This is not a model intelligence problem — no matter how smart the model, unstructured pricing pages are uncomputable. It's a **data problem**, and ASM solves it.

### The Solution

ASM provides three layers:

1. **Discover** — A registry of **70 real-world service manifests** across **47 taxonomy categories** (LLM, image generation, video, TTS, embedding, GPU, database, storage, and more). Each manifest declares pricing (12 billing dimension types), quality metrics (with `self_reported` vs independent benchmark flags), SLA (latency, uptime, rate limits), and an on-chain payment address.

2. **Evaluate** — A **TOPSIS multi-criteria decision engine** (Python + TypeScript parity verified) that ranks candidates by cost, quality, speed, and reliability with configurable preference weights and hard constraints. Discovery accuracy: **72% top-1 taxonomy match** across diverse tasks. A/B tested against random selection with statistical significance (**p=0.048**).

3. **Pay** — Each `/api/score` call resolves a winner and settles **$0.005 USDC** directly to that provider's on-chain address via **Circle Gateway's x402 batching protocol** on Arc testnet. No manual wallet wiring. One endpoint, N recipients.

### Hackathon Requirements — All Met

| Requirement | Status | Evidence |
|---|---|---|
| Per-action pricing ≤ $0.01 | **PASS** | **$0.005/tx avg** (range $0.001–$0.005) |
| 50+ on-chain transactions | **PASS** | **50/50 settled**, 0 failed, 15 unique recipients |
| Margin explanation provided | **PASS** | Lightning-style batching: Circle Gateway authorizes off-chain, settles on-chain in batches. Per-tx gas → ~$0. On Ethereum L1 same 50 tx would cost $25–$250 in gas alone. **~5,000× overhead eliminated.** |
| Uses Arc + USDC + Nanopayments | **PASS** | Arc Testnet (`eip155:5042002`) · USDC · Circle GatewayWallet contract |

### Track Declaration: Per-API Monetization Engine (primary)

ASM implements exactly this track: every individual API call is a monetizable event. An agent decomposes a task into 50 subtasks; each subtask triggers one `POST /api/score`; each score produces one ranked winner; each winner receives one sub-cent USDC payment. The entire loop is autonomous, auditable, and settled on-chain.

**Naturally aligns with Agent-to-Agent Payment Loop** — every score call is a real-time machine-to-machine settlement with no batching delay or custodial control.

**Also submitted to the Google Track**: Gemini 2.5 Flash Function Calling drives the agent reasoning loop. The agent is given a natural-language task plus 30 ASM taxonomies and emits a structured `select_taxonomy_and_score(taxonomy, reasoning)` function call that triggers Circle x402 settlement. Reproducible at `discovery/scripts/fc-test-raw.cjs` — **4/5 (80%) routing accuracy** across diverse tasks (image gen, translation, code, TTS, scraping).

### Tech Stack

- **Settlement layer**: Arc Testnet + USDC + Circle Gateway (`@circle-fin/x402-batching`)
- **Scoring engine**: TOPSIS + Weighted Average + Trust Delta (Python stdlib / TypeScript)
- **Discovery pipeline**: LangGraph state machine (embed → retrieve → rerank → select)
- **AI reasoning**: **Gemini 2.5 Flash via Function Calling** to Circle x402 endpoints (Google track requirement satisfied), with fallback chain: Gemini → OpenRouter → OpenAI
- **Trust layer**: 3-layer architecture (Transparency → Verification → Signed Receipts) aligned with ERC-8004 computable trust dimensions
- **Registry**: MCP Server (5 tools) + HTTP REST API + 70 manifests

### Live Links

- **Dashboard demo**: https://asm-arc-circle-2026.vercel.app/
- **Marketplace**: https://asm-arc-circle-2026.vercel.app/marketplace
- **Source code**: https://github.com/YE-YI7/asm-arc-circle-2026
- **On-chain proof**: Buyer wallet [`0xF5d4…b038`](https://testnet.arcscan.app/address/0xF5d426D5cdfaeB18Ea2cDec2F7c2CB88eEe6b038) · GatewayWallet [`0x0077…19B9`](https://testnet.arcscan.app/address/0x0077777d7EBA4688BDeF3E311b846F25870A19B9)

### Trust & ERC-8004 Alignment

ASM's trust model maps directly to ERC-8004's computable trust dimensions: every manifest carries a `self_reported` flag (provenance), references third-party benchmarks with URLs (verification), and integrates Signed Receipts (IETF ACTA draft) for post-hoc performance proof. The formula `trust_delta = |declared - actual| / declared` produces a quantifiable credibility score that updates automatically with each transaction — making the payment-to-verification loop self-sustaining.

**Open source · MIT License · github.com/YE-YI7/asm-arc-circle-2026**

---

## 4. Technology & Category Tags

```
Arc, USDC, Circle Nanopayments, Circle Gateway, x402, TOPSIS, LangGraph, Gemini, Function Calling, AI Agents, Agent Commerce, Marketplace, Stablecoins, Multi-Criteria Decision Making, MCP Server, Tokenized Economy, Settlement Layer, Sub-cent Payments, Autonomous Agents, Service Discovery, OpenAPI, ERC-8004, Signed Receipts, Hackathon
```
