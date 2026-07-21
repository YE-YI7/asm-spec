# ASM × x402 — the "which to buy" layer above "how to pay"

[x402](https://github.com/coinbase/x402) lets an agent pay for an HTTP resource over the `402 Payment Required` status code, and its [`bazaar`](https://github.com/coinbase/x402/blob/main/specs/extensions/bazaar.md) extension lets facilitators **discover and catalog** paid endpoints. Between discovery and payment sits a decision x402 deliberately doesn't make: **among several substitutable paid endpoints, which one should this agent actually buy from?**

Cheapest-wins is the naive default, and it fails in two ways price alone can't see:

1. the cheapest endpoint **violates a hard user constraint** (e.g. it trains on the user's query data);
2. an autonomous agent picks a **`negotiated`** endpoint it can never transact with — the select-then-402 dead end the [ai-catalog monetization discussion](https://github.com/Agent-Card/ai-catalog/issues/83) also flags.

## The bridge

ASM rides the surface x402 **already exposes**: the `402` response's open `extensions` object. Value/selection metadata travels in `extensions.asm`, right next to `extensions.bazaar`. No x402 spec change — the same rider pattern ASM uses for MCP `_meta` and AI Catalog `metadata`.

```
extensions: {
  bazaar: { info: { input, output } },   // how to call it        (x402)
  asm:    { taxonomy, quality_score,     // which to pick, and whether allowed
            data_governance, risk_class, approval }
}
```

The agent reads **price** from `accepts`, **value/eligibility** from `extensions.asm`, gates, ranks — and only pays the winner.

## Run

```bash
python integrations/x402/asm_x402_bridge.py
```

Self-contained: the 402 responses are spec-accurate x402 v2 (atomic USDC amounts, `eip155:84532` = Base Sepolia **testnet**, USDC asset), so it runs with no network and no funds. The settlement step is a clearly-labelled testnet-shaped **mock** — it constructs the `X-PAYMENT` payload but does not sign or submit.

## What the demo shows

A trading-bot agent (budget $0.02/call, must-not-train-on-my-data, autonomous) choosing among four BTC-price endpoints: cheapest-wins would pay a $0.005 tool that trains on user data; ASM gates that out (plus the over-budget and negotiated ones) and pays the eligible best-value $0.01 tool instead.

## Scope / honesty

This is a demonstration of the **decision layer**, not a payment implementation. Real settlement, signing, and mainnet flow belong to x402 clients/facilitators; ASM's job ends at "pay this one, for these reasons." Wiring the mock settlement to a real testnet facilitator is the next step.
