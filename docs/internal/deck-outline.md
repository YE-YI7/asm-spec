# Deck outline — 12 slides

> **Target length**: 12 slides, ~8 minutes spoken. For lablab we upload as PDF; for a live pitch it's the same deck.
> **Aesthetic**: dark navy background (#0B1220), accent color Arc-orange (#FF6B35), body text white, mono font for code and numbers.
> **Tool**: use Keynote or Figma Slides — avoid PowerPoint's default templates; they scream "student project." If you use Google Slides, pick the "Focus" theme dark variant and restyle.
> **Exported**: PDF at 1920×1080, 16:9, under 10 MB.
> **Deadline**: v1 by 4/22 EOD, v2 by 4/23 EOD, frozen 4/24 AM.
> **Owner**: Caleb fills it, Eiddie reviews visuals, Hak + Hamza review technical claims

---

## Slide 1 — Title

**Visual:** centered. Dark background. Large wordmark:

```
ASM
```

Subtitle:
```
The Selection Layer for Agentic Commerce
```

Small bottom line:
```
Arc × Circle Hackathon 2026 · lablab
```

Speaker note (5s): *"Hi, I'm Caleb. Today I want to show you the layer of agent commerce nobody's built yet."*

---

## Slide 2 — The problem in one chart

**Visual:** a split screen.

Left: an AI agent cartoon, facing FIVE copies of "Image Generation Service" — each with a different price and quality. The agent has a `?` over its head.

Right: a table with 1 row per criterion (Price, Quality, Latency, Uptime) × 5 columns (the services), but the cells are all blank — because the data doesn't exist in a structured form today.

**Headline:** *"Agents have no structured way to choose."*

**Body caption:** *"Same capability, wildly different price and quality. Today agents guess or pick the loudest brand — 3–10× cost overrun is routine."*

Speaker note (30s): *"When an agent faces five providers that can all generate an image, it has no machine-readable data to compare them. OpenAPI tells it what each can do, but not what each is worth. So it guesses. And in production that guess costs 3 to 10× more than a principled pick would."*

---

## Slide 3 — The 4-layer stack (our most memorable slide)

**Visual:** a clean 4-layer diagram, bottom to top:

```
┌────────────────────────────────────────┐
│  Circle + Arc   →   How do we pay?       │  ✅
├────────────────────────────────────────┤
│  ASM            →   Which provider, why? │  ← us
├────────────────────────────────────────┤
│  ERC-8004       →   Can we trust this?   │  ✅
├────────────────────────────────────────┤
│  MCP            →   What can it do?      │  ✅
└────────────────────────────────────────┘
```

**Headline:** *"ASM is the missing layer between MCP and Circle."*

Speaker note (30s): *"The agentic commerce stack has four layers. Three of them are solved. MCP answers what a tool can do. ERC-8004 answers whether an agent can be trusted. Circle and Arc answer how payments settle. The gap is 'which provider, and why.' That's ASM."*

---

## Slide 4 — Meet Campaign

**Visual:** a mock dashboard. A chat bubble from a user: *"Launch FocusBear globally."*

A single card in the center labeled "Campaign — AI marketing agent" with a subtitle *"decomposes the brief into 50 sub-tasks across 15 service categories."*

A thin list beneath shows 6 sample sub-tasks:
- Generate hero image (1024×1024)
- Translate caption to Japanese
- Voiceover script, 30s
- Scrape competitor engagement
- Embed 10 captions, cluster
- Deploy landing page

**Headline:** *"One brief. Fifty specialists. All paid on-chain."*

Speaker note (15s): *"Meet Campaign. She's our worked example — an AI marketing agent who decomposes one founder brief into 50 specialist purchases. Images, translations, voiceovers, scrapes, deploys. Fifty sub-tasks, fifteen categories."*

---

## Slide 5 — ONE decision, expanded (the hero)

**Visual:** this is the deck's most important slide. Three candidate cards fan out of a central taxonomy node labeled `ai.vision.image_generation`:

| DALL·E 3 | Imagen 3 | FLUX 1.1 Pro |
|---|---|---|
| $0.040 | $0.040 | $0.040 |
| Trust 0.85 | Trust 0.88 | **Trust 0.90** |
| Score 0.643 | Score 0.812 | **Score 0.832** ✓ |

Arrow from FLUX 1.1 Pro → Campaign's wallet → *flies off screen as USDC*.

Caption box: *"FLUX 1.1 Pro wins on trust (0.90) among 3 candidates; +0.020 ahead of Imagen 3. Paid 0.004 USDC, 2.3s, Arc testnet tx →"*

**Headline:** *"One decision in 2.3 seconds — priced, scored, settled."*

Speaker note (30s): *"Here's the unit of work. Campaign needs a hero image. ASM returns three candidates from its registry of seventy real services. The scorer ranks them. FLUX wins on trust, just ahead of Imagen. Circle's x402 protocol settles the payment — 0.4 cents in USDC, directly to FLUX's Arc testnet address. Two point three seconds. Every field auditable."*

---

## Slide 6 — Scale reveal: 50 decisions, 15 recipients

**Visual:** Sankey diagram — Campaign's single wallet on the left → fifteen provider addresses on the right, arrows thickness proportional to tx count.

Three big numbers below:

```
50 purchases
15 unique recipient addresses
$0.25 total · 12 seconds
```

**Headline:** *"50 decisions · 15 recipients · 12 seconds · $0.25 total."*

Speaker note (30s): *"Campaign does this fifty times. Because the scorer is running on fifteen different categories, the money naturally fans out to fifteen different provider addresses. Total spend, twenty-five cents. Total time, twelve seconds. This isn't a demo stitched together — it's the output of one benchmark run."*

---

## Slide 7 — "This isn't a marketing tool" (generalizability)

**Visual:** a hub-and-spoke diagram. ASM in the center. Four spokes out:

- Coding agent → `dev.ide.completion` taxonomy
- Research agent → `tool.data.search` taxonomy
- Support agent → `ai.nlp.qa` taxonomy
- Trading agent → `fin.market.quotes` taxonomy

Each spoke labeled with `discoverTaxonomy(task) → ...`

**Headline:** *"Campaign is one example. ASM is the protocol."*

Speaker note (20s): *"Campaign is a worked example, not the product. The same ten lines of code route any agent's any sub-task to any provider in the registry. Coding agents. Research agents. Support. Trading. ASM reads a taxonomy and a preference vector — it doesn't care what domain the caller is in."*

---

## Slide 8 — Why this couldn't exist before (economics)

**Visual:** a 3-row table, large type. Each row: payment size, L1 gas, viability.

| Payment | Ethereum L1 gas | Viable? |
|---|---|---|
| $0.005 per image | $0.50 – $5.00 | ❌ 100–1000× overhead |
| $0.001 per embedding | $0.50 – $5.00 | ❌ 500–5000× overhead |
| $0.005 on Arc + Circle | **≈ $0.000** | ✅ |

**Headline:** *"Sub-cent agent payments are impossible on L1. Arc makes them possible. ASM makes them smart."*

Speaker note (30s): *"A half-cent payment with five dollars of gas is economically impossible. Every agent builder who wants per-query pricing hits this wall. Arc plus Circle Nanopayments batch thousands of transfers into one settlement — per-transaction fees collapse toward zero. That's what lets agents actually transact per-call instead of per-subscription."*

---

## Slide 9 — What's in the box

**Visual:** four quadrants, each a small code/screenshot tile:

- **Registry**: 70 live manifests, 47 taxonomies (screenshot of `manifests/` directory listing)
- **Scorer**: TOPSIS + weighted average, Python ↔ TS cross-verified (3 passing unit tests)
- **Payments**: x402 with dynamic payTo on Arc testnet, mock-mode + live-mode (code snippet)
- **Tools**: `asm-lint` CLI for auditing any MCP server (one-line command)

**Headline:** *"Open protocol. Real manifests. Real scorer. Real payments."*

Speaker note (20s): *"We didn't ship slides. We shipped a protocol. Seventy manifests representing real services with real pricing. A scorer that passes cross-language parity tests. A payments module with real Arc settlement. And a linter so any MCP server author can check their manifest quality."*

---

## Slide 10 — Architecture (for the technical judge)

**Visual:** sequence diagram:

```
Campaign      ASM Registry      Scorer         x402/Circle       Arc testnet
   │              │               │                 │                 │
   │─ query  ────▶│               │                 │                 │
   │              │── candidates ▶│                 │                 │
   │◀── winner + reasoning ───────│                 │                 │
   │                                                │                 │
   │─ POST /api/score (body: { taxonomy }) ────────▶│                 │
   │                             dynamicPayTo(body) → winner.onchain_address
   │                                                │──  USDC  ──────▶│
   │◀── 200 OK + tx hash ─────────────────────────────────────────────│
```

**Headline:** *"One HTTP route pays N different recipients — dynamically."*

Speaker note (20s): *"The novel bit of plumbing: Circle's x402 supports a `payTo` *function*, not just a static address. We plug our scorer into it, so the winner for each request is resolved at request time. One route, hundreds of recipients."*

---

## Slide 11 — The team & the roadmap

**Visual:** 4 team avatars with single-line bios:

- Caleb Guo — Protocol design + backend · China
- Hamza Atiq — Live Arc + Circle · Pakistan
- Hak (hakanttek) — Skill Discovery / LangChain · Germany
- Eiddie — Frontend & visuals · [TBD]

Right half: checkmarked roadmap:
- ✅ 70 real manifests
- ✅ TOPSIS scorer with on-chain scoring
- ✅ x402 dynamic payTo
- ✅ 50-tx Arc testnet benchmark
- ⏳ Skill Discovery integration
- ⏳ Crawler pipeline (post-hackathon)
- ⏳ SEP ratification (MCP community)

**Headline:** *"Open protocol. Four builders. Ready to grow."*

Speaker note (15s): *"We're four people across four countries. Everything you see in the demo is in the public repo under MIT. The SEP proposal to the MCP community is already submitted. If you're building an agent and want to publish a manifest, come find us."*

---

## Slide 12 — Close

**Visual:** full-screen single line:

```
github.com/YE-YI7/asm-arc-circle-2026
```

Beneath:
```
MCP · ERC-8004 · ASM · Circle + Arc
The full agentic commerce stack.
```

Speaker note (10s): *"Thank you. The repo is open, the demo is live, the protocol is documented. Come build with us."*

---

## Visual asset checklist

Eiddie, these are the visuals we actually need to produce for the deck (text alone won't carry it):

- [ ] **4-layer stack diagram** — SVG, reusable in README, deck, video
- [ ] **Hero shot still** — three candidate cards + score bars + arrow to winner
- [ ] **Sankey diagram** — Campaign wallet → 15 provider addresses
- [ ] **Hub-and-spoke generalizability diagram** — ASM center, 4 agent types around
- [ ] **Economics table** — nicely typeset, NOT a raw markdown table on screen
- [ ] **Sequence diagram for slide 10** — render via mermaid or sketch clean

If any of these take more than 1 hour each, use a simpler version — they should support the speaker, not be the focus.

---

## "Don't do" list

- Don't include code screenshots in the deck. If a judge wants code, they click the repo. Deck is for story.
- Don't put more than 3 numbers on a single slide — your hit rate per slide drops.
- Don't use emoji shotgun. One accent emoji per slide, max.
- Don't write full paragraphs — every bullet should be ≤ 10 words.
- Don't animate transitions — they eat the judge's patience.
