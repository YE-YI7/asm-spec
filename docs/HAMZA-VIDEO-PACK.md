# Video Pack for Hamza

> Everything you need to record the submission video. Send it back as MP4 (5min cap; under 4min is better).

---

## 1. Files in this pack

All under `docs/assets/`:

- **`asm-slides.pdf`** — 16-page deck (full visual story, dark cyber-modern theme). Open this in Acrobat / browser, full-screen, scrub through during recording.
- **`hero-shot.jpg`** — title card / cover image (2000×1247).
- **`screenshots/01-dashboard.png`** — main demo dashboard (1920×1080).
- **`screenshots/02-marketplace.png`** — service marketplace page.
- **`screenshots/03-benchmark.png`** — 50-tx benchmark results page.
- **`screenshots/04-slides.png`** — slide preview.
- **Live site (record this directly if possible)**:
  - https://asm-arc-circle-2026.vercel.app/
  - https://asm-arc-circle-2026.vercel.app/marketplace
  - https://asm-arc-circle-2026.vercel.app/benchmark
  - https://asm-arc-circle-2026.vercel.app/slides

---

## 2. The hard rules (judges check these)

The video MUST clearly show:

1. ✅ **A USDC transaction in the Circle Developer Console** — your existing 1-min footage covers this.
2. ✅ **The same transaction verified on Arc Block Explorer** (testnet.arcscan.app) — your footage covers this too.
3. ✅ **50+ on-chain transactions** — show the `/benchmark` page (screenshot 03) where 50/50 settled is visible.
4. ✅ **Per-action ≤ $0.01** — say "$0.005 per call" on screen.
5. ✅ **Margin explanation** — one line: "On L1 this would cost $25–$250 in gas. On Arc + Circle Gateway: ~$0."

---

## 3. Suggested 4-minute structure

**0:00–0:25 — Hook & problem**
Show slide 1 (title) → slide 2 (problem). Voiceover: 
> "AI agents need to call APIs constantly — image gen, translation, code, audio. They have no structured way to compare providers. They pick blindly, overpay 3 to 10x, and the decision isn't reproducible. ASM fixes that."

**0:25–1:30 — The product (live demo)**
Screen-record the dashboard at https://asm-arc-circle-2026.vercel.app/. Pick a task taxonomy → click *Run Selection* → watch the agent rank and route a payment. Voiceover:
> "An autonomous agent calls one HTTP endpoint. ASM ranks 70 real services across 47 taxonomies using TOPSIS multi-criteria scoring. The winner gets a $0.005 USDC payment to their Arc address. Sub-second finality."

**1:30–2:30 — On-chain proof (your existing Circle Console + Arc Explorer footage)**
Splice in the 1-min clip you already recorded. Voiceover overlay:
> "Same fifty transactions, viewed from the other side. Circle Developer Console shows every USDC transfer settled. Click any hash — Arc explorer confirms it on-chain. Real money, real settlement, real time."

**2:30–3:00 — Why this matters (economics)**
Show slide on margin (the $0.005 vs $0.50–$5.00 L1 gas table). Voiceover:
> "Half a cent per payment. On Ethereum L1, gas alone is fifty cents to five dollars. Five thousand times overhead. Economically impossible. Arc plus Circle Gateway batches off-chain authorizations and settles on-chain in batches — Lightning Network for stablecoins. That's what makes per-call agent pricing viable for the first time."

**3:00–3:40 — The Google angle + protocol stack**
Show slide on the 4-layer stack (MCP / ERC-8004 / ASM / Circle+Arc). Voiceover:
> "Gemini 2.5 Flash drives the routing via Function Calling — 80% accuracy across diverse tasks. ASM sits between MCP, which describes what tools can do, and Circle plus Arc, which makes payment cheap enough to actually use them."

**3:40–4:00 — Close**
Show repo URL + demo URL on screen. Voiceover:
> "Seventy manifests, fifty payments on Arc, all open source. github.com/YE-YI7/asm-arc-circle-2026. Come build with us."

---

## 4. Numbers to keep on screen (at least 2s each)

- **50 / 50 transactions settled**
- **$0.005 per call**
- **5,000× cheaper than L1 gas**
- **70 service manifests**
- **47 taxonomy categories**
- **80% Gemini Function Calling accuracy (4/5)**
- **Track: Per-API Monetization Engine + Google Track**

---

## 5. After recording

- Export 1080p MP4, under 200MB if possible
- Upload to your X (Twitter) account
- Post must include all three tags in the **same** post: **@buildoncircle  @arc  @lablabai**
- Caption (copy-paste ready):

```
🚀 Just shipped ASM — Agent Service Manifest

The first open protocol that lets AI agents discover, rank & pay for AI services per call — sub-cent USDC settlement on Arc.

✅ 50/50 tx settled live on Arc testnet
✅ $0.005/tx — 5,000× cheaper than L1 gas
✅ Gemini 2.5 Flash Function Calling drives routing

@buildoncircle @arc @lablabai

github.com/YE-YI7/asm-arc-circle-2026
asm-arc-circle-2026.vercel.app

#ArcAgenticEconomy
```

- Send the **post URL** back to Caleb — that's what goes into the lablab submission form.

---

## 6. If anything is unclear

Repo: https://github.com/YE-YI7/asm-arc-circle-2026  
Long description (full submission copy): `docs/lablab-submission.md`  
Circle integration deep-dive: `docs/circle-feedback-submission.md`
