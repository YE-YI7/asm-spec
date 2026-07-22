# ASM positioning (canonical)

The one source for how we describe ASM. Keep public surfaces (README, paper, HF card, showcase, launch posts) consistent with this. Name stays **ASM / Agent Service Manifest**; the tagline, not the name, carries the layer framing.

## One-liner

> ASM is the **selection layer** for agents — between discovery (MCP/ARD/AI-Catalog) and settlement (x402/AP2/ACP) — deciding which tool an agent *can* use, *should* use, and therefore *who gets the work and the money*.

## The stack

```
Discovery    MCP · ARD · AI-Catalog      what tools exist            (Anthropic/Google/AWS)
Selection    ASM  ← unfilled slot        eligibility + value + who gets paid
Settlement   x402 · AP2 · ACP            how the payment executes    (Coinbase/Google/Visa)
```

The neighbours are being built by the largest players; the middle is open. We don't compete with discovery or settlement — we're the missing hand-off between them.

## Why "selection layer," not "metadata spec"

Metadata is passive and absorbable — AI Catalog `metadata`/`extensions`, MCP `_meta`, Arcade `extras` can all swallow our fields. The durable, non-commoditizable position is the **selection function** itself (which provider gets chosen → gets paid). Metadata is the substrate; selection is the product. (Industry thesis, noted: rent accrues to settlement + trust, not to Layer-2 specs — which is exactly why we must be the operating selection point, not just a schema.)

## Differentiation (answers to "how are you different from X")

- **vs discovery (MCP/ARD/AI-Catalog):** they answer *what exists*; we answer *which one*.
- **vs settlement (x402/AP2):** they answer *how to pay*; we answer *whom to pay, and whether to*.
- **vs brand.context / AIVO decision-stage:** that's B2C brand-published evidence for *shopping recommendation*; ASM is *agent-operational* tool selection (uniquely: can the agent even drive it — invocability/eligibility — plus operational risk/approval).
- **vs orchestration platforms (MS Agent Framework, LangGraph):** they coordinate agents *within a system*; ASM selects *across third-party vendors*.

## The honest guardrail (do not cross)

A layer with no traffic is a claim, not a fact. Zero external adopters route selection through ASM today. So every surface says **"the layer we're building, with receipts"** — never "the layer agents use." Receipts we do have: a measured benchmark (ToolSelect-Bench), a working gated selector, a live on-chain selection→settlement demo.

## What "adoption" now means (sharpened)

Not "someone publishes our fields." **One real agent or gateway routing an actual selection decision through ASM** — demand or supply side. One real selection flow > a hundred nods. Bruce's Pipeworx gateway is the closest live candidate.

## Landscape note (shows we know the field — anti-slop)

"The selection layer is missing" is now an independently-recognized thesis (aivojournal, mintBlue, Medium think-pieces, Eco's 7-layer stack). We are not first to *name* the gap; we aim to be first to fill the *agent-operational* sub-slot **with a working, measured implementation** rather than a working paper.
