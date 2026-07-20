# ASM — Video Script v0

> **Target length**: 3:00 (lablab typical cap). Aim for 2:45 so we have 15s buffer.
> **Language**: English voiceover, English on-screen captions.
> **Tone**: confident, specific, no jargon-first. Numbers on screen at every scene cut.
> **Draft date**: 2026-04-21
> **Status**: FIRST DRAFT — pre-record read-through with Caleb on 4/22 EOD

---

## 0. Cold open (0:00 – 0:15) — "who is Campaign"

**On screen:** a clean dashboard boots up. A single card at center: "Campaign — AI marketing agent". Underneath: one line of input from a user — *"Launch FocusBear globally."*

**Voiceover:**
> Meet Campaign. She's an AI marketing agent. Thirty seconds ago, a founder asked her to launch an app globally. Now she needs to buy fifty different services — images, copy, translations, voiceovers, scrapes — from fifty different specialists.
>
> In today's agent economy, she has no structured way to choose between providers. She just picks the one she's heard of. We fixed that.

**On-screen caption at 0:12:** `ASM — the selection layer for agentic commerce`

---

## 1. The hero shot — one decision, expanded (0:15 – 0:50)

**On screen:** Campaign's first sub-task appears: *"Generate a hero image for the ADHD audience, 1024×1024."* The screen zooms into ASM.

Three candidate cards fan out from a central `ai.vision.image_generation` node:
- DALL·E 3 — $0.040, trust 0.85
- Imagen 3 — $0.040, trust 0.88
- FLUX 1.1 Pro — $0.040, trust 0.90

Score bars fill in. FLUX 1.1 Pro lights up.

A one-line caption appears: *"FLUX 1.1 Pro wins on price + trust, +0.643 ahead of Imagen 3."*

A USDC coin flies from Campaign's wallet to FLUX's Arc address. An Arc Explorer link flashes on screen.

**Voiceover:**
> Here's how one purchase works. Campaign needs a hero image. ASM returns three candidates from its registry of seventy real services, scores them on price, trust, and latency, and picks FLUX 1.1 Pro.
>
> Payment settles in under a second — zero-point-zero-zero-four dollars in USDC, paid directly to FLUX's Arc testnet address via Circle's x402 protocol.
>
> One decision. Two-point-three seconds. On-chain, auditable, explainable.

---

## 2. Scale reveal — 50 tx punchline (0:50 – 1:25)

**On screen:** the camera zooms out. Fifty decisions stream down the left column — taxonomy, winner, price, tx hash — faster and faster until they blur.

On the right, a Sankey diagram fans out: Campaign's single wallet on the left, fifteen provider addresses on the right, USDC arrows animating in.

**Numbers appear, one by one in large type:**
- 50 purchases
- 15 unique recipients
- $0.25 total spend
- 12 seconds wall-clock

**Voiceover:**
> Campaign does this fifty times. Fifty different sub-tasks. Fifteen different providers across fifteen service categories.
>
> Total spend: twenty-five cents. Total time: twelve seconds. Every single transaction visible on Arc Explorer.

**On-screen caption (1:20):** `All 50 tx on Arc testnet → [QR code / short URL to explorer]`

---

## 3. Generalizability beat (1:25 – 1:45) — "this is not a marketing tool"

**On screen:** Campaign fades. Four other agent avatars appear in a grid — a coding agent, a research agent, a customer-support agent, a trading agent — all wired to the same ASM node.

**Voiceover:**
> Campaign is one worked example. ASM is a protocol.
>
> The exact same ten lines of code route any agent's any sub-task to any provider in the registry. Coding agents pick IDEs. Research agents pick search APIs. Support agents pick knowledge bases. The selection layer is universal.

---

## 4. Why this couldn't exist before (1:45 – 2:15) — the economics

**On screen:** side-by-side table animates in:

| Payment size | Ethereum L1 gas | Viable? |
|---|---|---|
| $0.005 per image | $0.50 – $5.00 | 100×–1000× overhead ❌ |
| $0.001 per embedding | $0.50 – $5.00 | 500×–5000× overhead ❌ |

Then the Arc row lights up:
| $0.005 on Arc + Circle | ~$0.000 | ✅ |

**Voiceover:**
> A five-tenths-of-a-cent payment, with traditional Ethereum gas, costs fifty cents to five dollars. The fee dwarfs the payment a hundred to a thousand times. Economically impossible.
>
> Arc plus Circle Nanopayments batch thousands of USDC transfers and collapse per-transaction fees toward zero. That's what makes per-query agent pricing viable for the first time.
>
> ASM supplies the missing piece: *which* provider gets paid, and *why*.

---

## 5. Protocol stack close (2:15 – 2:45)

**On screen:** the 4-layer stack diagram draws itself:

```
MCP            "what a tool can do"            ✅ Anthropic
ERC-8004       "is this agent trustworthy?"    ✅ EVM community
ASM            "which provider is the right one?"   ← us
Circle + Arc   "how do we actually pay?"       ✅ Circle
```

**Voiceover:**
> MCP answers what a tool can do. ERC-8004 answers whether an agent can be trusted. Circle plus Arc answers how payments settle. ASM fills the gap in between: which provider, and why.
>
> Four layers — the agentic commerce stack is finally complete.
>
> Seventy manifests live, fifty payments on Arc, and an open protocol anyone can publish to. Come build with us.

**On-screen final card (2:40–2:45):**
```
ASM — Agent Service Manifest
github.com/YE-YI7/asm-arc-circle-2026
Built on Arc + Circle · lablab hackathon 2026
```

---

## Timing table (for Caleb while recording)

| Scene | Start | End | Length |
|---|---|---|---|
| Cold open | 0:00 | 0:15 | 0:15 |
| Hero shot | 0:15 | 0:50 | 0:35 |
| Scale reveal | 0:50 | 1:25 | 0:35 |
| Generalizability | 1:25 | 1:45 | 0:20 |
| Economics | 1:45 | 2:15 | 0:30 |
| Stack close | 2:15 | 2:45 | 0:30 |
| **Total** | | | **2:45** |

15-second buffer for natural pauses and a final breath before the card.

---

## Recording notes (Windows)

**Screen-record tool**: use **OBS Studio** (free, Windows, best quality).
- 1920×1080, 60fps, NVENC h264 encoder
- Capture source: dashboard live URL window (NOT the full desktop)
- Separate audio track for voice, record it with a quiet room + USB condenser mic if possible

**Voiceover**: record after all visuals are locked. Don't try to sync live. Use **Audacity** to record + denoise.
- Read each scene twice, pick the better take in edit.

**Editor**: **DaVinci Resolve** (free, handles 4K, has title animation). Avoid Windows Movie Maker / Clipchamp — looks amateur.

**Watch-for list before final export:**
- [ ] All on-screen text is spelled correctly (Circle, Arc, Nanopayments — capitalisation matters)
- [ ] All three key numbers are visible at least 2 seconds each: **50, 15, $0.25**
- [ ] Arc Explorer URL is legible in at least one frame
- [ ] Video plays without sound still communicates the pitch (captions on every scene)
- [ ] Final card URL is correct

---

## Backup GIF plan

**Why**: if the live URL is down during judging, a 20-second looping GIF of the hero shot (scene 1) lives at the top of the README. Judges see the money shot even with no click.

**How**:
- Record scene 1 from the live dashboard once it ships (4/24 AM).
- Export as 900×600 @ 15fps, under 10 MB, using `ffmpeg -i hero.mp4 -vf "fps=15,scale=900:-1" hero.gif`.
- Drop at the top of README.md with alt text `ASM picks one winner from candidates and pays them in USDC on Arc`.

---

## Risks

- **Voiceover quality**: if my accent is hard to understand for non-native speakers, consider an AI voice clone via ElevenLabs (30-min job, $5).
- **On-screen math legibility**: the economics table must render large enough to read on a phone. Test on a 6-inch screen before locking.
- **Music**: pick royalty-free, background only, no vocals. YouTube Audio Library's "Inspirational Corporate" category is safe. Avoid anything dramatic — the numbers carry the drama.
