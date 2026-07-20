# lablab submission form — pre-filled draft

> **Deadline**: 2026-04-26
> **Strategy**: every text field answered in advance, then tightened on 4/25
> **Owner**: Caleb pastes, Hamza reviews the economics section, Hak reviews the Discovery section

---

## Project Title
**ASM — The Selection Layer for Agentic Commerce**

*(alt short: "ASM — Yelp for AI Agents")*

---

## Short Description (≤ 200 chars)
> ASM lets AI agents pick the right provider for every sub-task — not just pay each other. A scoring layer over 70 real services, with USDC settlement on Arc via Circle's x402 protocol.

(198 chars — under limit)

---

## Long Description (1–2 paragraphs)

> When an AI agent has fifty sub-tasks to run — images, translations, scrapes, code — it faces the same question fifty times: *which provider?* Today it has zero structured data to answer that. It guesses, or picks whichever brand is loudest. ASM fixes this with a protocol: every service publishes a machine-readable manifest of its price, quality, and trust, and a scorer picks the winner per task.
>
> We built a full agent-to-agent payment loop on top. Campaign, an AI marketing agent, launches an app globally by firing 50 purchases across 15 service categories. ASM scores 2–5 candidates per task, Circle's x402 protocol dynamically routes USDC to the winner's Arc testnet address, and funds fan out to 15 distinct provider addresses — all in 12 seconds for $0.25 total. On Ethereum L1 the same fifty payments would cost about $50 in gas alone. ASM is the missing layer between MCP (what a tool can do) and Circle+Arc (how payments settle): *which provider, and why*.

---

## Technology & Category Tags
- AI Agents
- Agent-to-Agent Payments
- Circle Arc
- USDC
- Circle Nanopayments
- x402 Protocol
- MCP (Model Context Protocol)
- TypeScript
- TOPSIS (multi-criteria scoring)

---

## GitHub Repository
`https://github.com/YE-YI7/asm-arc-circle-2026`

---

## Live Demo URL
`https://asm-demo.vercel.app` *(Eiddie — confirm this is the deployed URL by 4/24 EOD)*

---

## Video URL
*(populate after upload to YouTube on 4/25)*

---

## Presentation Deck URL
*(populate after hosting deck PDF on 4/25, likely via the GitHub Release attachment)*

---

## Cover Image
- 1200×630 PNG
- Design: dark background, 4-layer stack diagram (MCP / ERC-8004 / ASM / Circle+Arc), tagline *"ASM — The Selection Layer for Agentic Commerce"*
- Owner: Eiddie (one evening of work, 4/23 EOD)

---

## Circle Product Feedback (prize-eligible, $500 pool)

> We hit three concrete pain points with the Gateway + x402 stack on Arc testnet that are worth flagging:
>
> 1. **UUID ≠ on-chain tx hash.** `gatewayClient.pay()` returns a Circle UUID (e.g. `8b311212-…`), but the actual Arc transaction hash is only retrievable by scanning `USDC Transfer` events via an RPC like viem's `getLogs`. `getTransferById` returns status but never surfaces the hash. For any app that wants to show users an Arc Explorer link, this is a blocker without custom chain scanning.
>
> 2. **Batching cadence causes a 0–60 min delay between intent and on-chain settlement.** Transfers created at `HH:03` land on-chain at `(HH+1):00:06` — the hourly flush at the top of the hour plus ~6 seconds. For a demo loop this is fine; for a consumer payment UX (or for recording a hackathon video!) this is surprising. Document the cadence explicitly, or expose a "flush now" flag for testnet.
>
> 3. **x402's `payTo` accepts a function, which is powerful but undocumented.** We use dynamic `payTo` to route one route to N different recipients (scorer picks winner → payTo returns winner's address). It works beautifully but we had to discover the async-function signature by reading source. A short paragraph in the x402 README would save the next team a day.
>
> We love what Circle is building — these are friction points, not flaws. Happy to share more detail with the team on request.

---

## Why This Model Fails With Traditional Gas (mandatory economic justification)

> Sub-cent payments between agents are economically impossible on Ethereum L1. A $0.005 image generation payment costs $0.50 to $5.00 in gas — the fee dwarfs the transaction a hundred to a thousand times. For payment sizes under 1 cent, L1 gas imposes an overhead of 500× to 5,000×. No agent builder can ship per-query pricing at those numbers.
>
> Arc plus Circle Nanopayments collapse the fee to approximately zero by batching thousands of USDC transfers per settlement. Our 50-transaction benchmark cost a total of $0.25 — the identical 50 transactions on Ethereum L1 at 15 gwei would cost about $95, a ratio of roughly 380×. That's the gap between "possible in principle" and "viable as a product."
>
> ASM supplies the missing piece: *which* provider should receive each nanopayment, and why. Without that selection layer, agents default to the provider they've heard of — Arc makes sub-cent payments possible, ASM makes them *smart*.

---

## Track Statement
> Track: **Agent-to-Agent Payment Loop**. Campaign, an AI marketing agent, autonomously pays 50 different provider services in a single run, with all payments settled on Arc in USDC via Circle's x402 protocol.

---

## Team

- **Caleb Guo (kkkC)** — Protocol design, registry, scorer, x402 integration. China.
- **Hamza Atiq** — Live Arc testnet settlement, Circle credentials, submission QA. Pakistan.
- **Hak (hakanttek)** — Skill Discovery (LangChain-based natural-language → taxonomy mapping). Germany / Turkey.
- **Eiddie** — Frontend dashboard, hero-shot animations, cover image. *(location TBD)*

---

## Judging criteria alignment (for our own reference — DO NOT paste)

| Axis | Evidence we surface |
|---|---|
| Application of Tech | Arc Explorer links for 5+ real tx; Circle Dev Console screenshots; x402 dynamic payTo (novel use); 70 real manifests, not toy data |
| Presentation | Live demo URL; 2:45 video with hero shot; 12-slide deck; clean README; backup GIF in case URL is down |
| Business Value | $0.005 × 50 gas economics table; "50 real manifests, 15 recipients = real market" narrative; "selection layer" framing solves a real info-asymmetry problem |
| Originality | ASM-as-protocol + SEP proposal + 4-layer stack framing ("MCP + ERC-8004 + ASM + Circle"); Campaign persona gives the category a name |

---

## Pre-submission checklist (walk through this 4/25 AM)

- [ ] GitHub repo public, README above the fold tells the whole story in 30s
- [ ] README has backup GIF at the top (hero shot)
- [ ] Live demo URL loads in <2s from a fresh browser, in incognito mode
- [ ] Video uploaded to YouTube, unlisted at first then public on 4/26
- [ ] Deck PDF uploaded, link works
- [ ] Cover image uploaded, renders at 1200×630 without distortion
- [ ] At least 5 Arc Explorer URLs are visible in README and submission form
- [ ] Circle Developer Console screenshot in README
- [ ] "Why gas fails" paragraph present verbatim in both README and form
- [ ] Track explicitly stated in form
- [ ] Circle Product Feedback field filled (prize-eligible)
- [ ] All 4 team members named
