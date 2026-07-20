# Submission Checklist

> **Deadline**: 2026-04-25 10:00 (Beijing time buffer). Official submission window Apr 25.
> **Primary Track**: 🪙 Per-API Monetization Engine
> **Secondary alignment**: 🤖 Agent-to-Agent Payment Loop (every score call is also an A2A settlement)
> **Cross-submission**: 🏆 Google Track (Gemini 2.5 Flash Function Calling drives the routing loop)

---

## 🔴 HARD DISQUALIFIERS (must be done, or DQ)

- [ ] Real per-action pricing ≤ $0.01 demonstrated on-chain
- [ ] 50+ on-chain transactions visible in demo
- [ ] Margin explanation: why this fails with traditional gas ($0.05/tx × 50 = $2.50, kills any sub-cent model)
- [ ] Video shows Circle Developer Console + Arc Block Explorer verifying a tx
- [ ] Uses Arc + USDC + Circle Nanopayments
- [ ] Public GitHub repo MIT-compliant
- [ ] Circle Product Feedback field filled (see `circle-feedback-log.md`)
- [ ] Track explicitly stated in submission

---

## 📋 Required Submission Fields

### Basic
- [ ] Project Title: **ASM-Pay** (or final: "ASM — The Value Layer for Agentic Economy")
- [ ] Short Description (1–2 sentences)
- [ ] Long Description
- [ ] Technology & Category Tags

### Media
- [ ] Cover Image (1200×630 recommended)
- [ ] Video Presentation (3 min, see `video-script.md` — to be drafted 4/23)
- [ ] Slide Presentation (12 pages, see `deck-outline.md` — to be drafted 4/22)

### Code
- [ ] Public GitHub Repository URL: https://github.com/YE-YI7/asm-arc-circle-2026
- [ ] Demo Application Platform
- [ ] Application URL (live demo)

### Feedback (prize eligible)
- [ ] Circle Product Feedback — see `circle-feedback-log.md`

---

## 🎯 Judging Criteria Alignment (equal weight, each)

| Criterion | Our angle |
|---|---|
| **Application of Technology** | Arc + USDC + Nanopayments fully integrated; 50+ tx demo; positioned alongside ERC-8004 trust layer |
| **Presentation** | Clean narrative: "MCP + ERC-8004 + ASM + Circle = full agentic economy stack" |
| **Business Value** | Solves real problem: agents today have zero structured data to select services — info asymmetry erodes margin even when gas is solved |
| **Originality** | ASM as protocol + SEP-001 already drafted + ServiceNow Working Group interest (mention if Sugandh agrees) |

---

## 🎬 Demo Narrative (50+ tx version)

1. User asks CrabRes: "find cheapest image generation service that meets my quality bar"
2. CrabRes calls `asm_registry_lookup` tool → ASM registry returns 10 candidate MCP servers with manifests
3. ASM scorer ranks them by price × quality × SLA
4. CrabRes picks top 3 and **fires 50 sequential per-call payments** to compare real-world results
5. Each call = 1 Circle Nanopayment on Arc USDC (≤ $0.01 per call)
6. Dashboard shows: 50 txs, total cost, margin saved vs Ethereum mainnet
7. Final recipient/winner settled; Arc Block Explorer shows all 50 tx hashes

**This naturally produces 50+ tx AND demonstrates agent-to-agent payment loop AND shows margin math.**

---

## 🧨 Key risks

- **Risk**: 50-tx benchmark script takes longer than planned → **Mitigation**: write script 4/21, test early
- **Risk**: Per-action price display looks fake → **Mitigation**: show live Circle Dev Console + Arc explorer in video
- **Risk**: Deck and video eat all of 4/24 → **Mitigation**: deck outline on 4/22, first video draft on 4/23

---

## Daily submission prep checkpoints

- **4/22 EOD**: deck v1 outline done, tx benchmark script skeleton written
- **4/23 EOD**: deck v2 after review, 50-tx script tested green
- **4/24 EOD**: video v1 recorded, all text fields drafted
- **4/25 09:00**: final check, submit, leave 1h buffer for lablab platform issues
