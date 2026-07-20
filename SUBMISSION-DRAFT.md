# 📝 提交表单草稿 — Agentic Economy on Arc

> 提交前复制粘贴到 lablab.ai 提交表单

---

## Project Title

**ASM: Autonomous Service Selection + Payment for AI Agents**

---

## Short Description (≤100 words)

ASM (Agent Service Manifest) is an open protocol that lets AI agents autonomously discover, evaluate, and pay for services — per API call, at sub-cent precision, settled on Arc in USDC.

Using TOPSIS multi-criteria decision making, agents compare 70 real-world services across cost, quality, speed, and reliability. Each scoring request costs $0.005 USDC via Circle Nanopayments. No human in the loop. No hardcoded API keys.

Think of it as "Schema.org for AI service pricing" + "x402-powered pay-per-use."

---

## Long Description

### The Problem

When an AI agent needs to call an external service (LLM, image generation, TTS, etc.), it has **zero structured data** to choose between providers. Today's agents either hardcode a single provider or pick the most famous one — leading to 3-10x cost overruns or quality mismatches.

This is not a model intelligence problem — it's a **data problem**. No matter how smart the model, unstructured pricing pages are uncomputable.

### Our Solution

ASM provides three layers:

**1. Structured Service Manifests**
Every AI service publishes a machine-readable JSON manifest declaring its pricing, quality benchmarks, SLA, and payment methods. We've created 70 real manifests covering 47 categories — from LLMs and image generators to databases, email APIs, deployment platforms, and more.

**2. TOPSIS Multi-Criteria Scoring**
Agents send preference weights (e.g., "60% cost, 20% quality, 15% speed, 5% reliability") and receive a ranked list with explainable reasoning. The same algorithm runs in both Python and TypeScript with verified cross-language parity.

**3. Circle Nanopayments on Arc**
Every scoring/query API call is gated by x402. Agents pay $0.002–$0.005 USDC per call through Circle Gateway, settled on Arc Testnet. This creates a self-sustaining evaluation marketplace — agents pay for intelligence, not just compute.

### Why Nanopayments Are Essential

Traditional gas models make this impossible:
- Our payment per call: $0.002–$0.005
- Typical L1 gas: $0.01–$0.50
- **Gas exceeds the payment itself** → economically unviable

Circle Nanopayments + Arc solve this by batching settlements, enabling true sub-cent agent-to-agent commerce.

### What We Built

- **70 real-world service manifests** across 47 categories
- **TOPSIS scorer** (Python + TypeScript, cross-language verified)
- **x402 Payment Server** with Circle Gateway integration
- **Buyer SDK** with `GatewayClient.pay()` for autonomous agents
- **Trust Delta Engine** — post-payment service quality verification
- **Real-time Dashboard** — transaction monitoring and analytics
- **E2E Demo** — 14 agent personas, 55+ transactions, $0.243 USDC total

### Architecture

```
Agent receives task → Taxonomy mapping → ASM Registry query
→ TOPSIS scoring (pay $0.005 USDC via x402)
→ Service selection → Execution → Signed Receipt → Trust update
```

### Track Alignment

**Agent-to-Agent Payment Loop** — ASM demonstrates a complete cycle where agents autonomously discover services, evaluate options, pay per-use, and build trust through verified receipts.

---

## Technology Tags

- Circle Nanopayments
- x402 Protocol
- Arc Testnet
- USDC
- TypeScript
- Express.js
- TOPSIS (Multi-Criteria Decision Making)
- MCP (Model Context Protocol)

## Category Tags

- Agent-to-Agent Payment Loop
- AI Infrastructure
- Developer Tools
- Open Protocol

---

## Why Traditional Gas Models Can't Do This

*(比赛要求回答这个问题)*

Our use case involves **high-frequency, sub-cent transactions** between AI agents:

1. **Volume**: An agent might score 50+ services in a single decision cycle
2. **Value**: Each scoring call is worth $0.002–$0.005 USDC
3. **Speed**: Agents need sub-second settlement to maintain workflow

On traditional L1s:
- Ethereum mainnet: ~$0.50–$5.00 per tx → **100-1000x the payment amount**
- Even L2s: ~$0.01–$0.05 per tx → **2-10x the payment amount**

Circle Nanopayments on Arc solve this by:
- **Batching**: Multiple micro-payments settled in a single on-chain transaction
- **Near-zero marginal cost**: Each additional payment in a batch costs essentially nothing
- **USDC-native**: No volatile gas token, no price uncertainty

Without this, the entire "agent pays for intelligence" model is economically impossible.

---

## Demo Application URL

`http://localhost:4402/api/dashboard`

*(注：如果部署了，替换为公网 URL)*

## GitHub Repository

`https://github.com/YE-YI7/asm-spec`

---

## Cover Image Description

*(用于 Canva 或 AI 生成)*

**构图**：深色背景 (#0a0a0f)，中央是一个发光的网络图，节点代表不同的 AI 服务（用图标：🤖💬🎨🎵📹），节点之间有发光的连线，连线上标注 "$0.005 USDC"。

**左上角**：ASM 标志 + "Agent Service Manifest"
**右下角**：Circle + Arc 标志
**底部**："Discover → Evaluate → Pay → Verify"

**配色**：
- 背景: #0a0a0f
- 主色: #00d4ff (Circle 蓝)
- 辅色: #7b2ff7 (Arc 紫)
- 点缀: #00ff88 (成功绿)
