# ASM Launch Posts

Use these posts to launch ASM as a practical OpenRouter value router first, and a protocol second.

The first line should not be "I wrote a protocol." It should be "I built a CLI that picks AI models by cost, constraints, and metadata."

## Hacker News

Title:

```text
Show HN: ASM - rank OpenRouter models by cost, constraints, and metadata
```

Body:

```text
I built Agent Service Manifest (ASM), a small CLI/protocol experiment for choosing AI services from structured value metadata.

The useful part today: ASM can rank live OpenRouter models without writing manifests first:

    asm openrouter 'cheap coding model under $0.50 per 1M tokens'
    asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'

It turns provider metadata into comparable manifests: pricing, capabilities, provenance, verification status, and usage signals. It can also emit router snippets for LiteLLM, Vercel AI SDK, and LangChain.

The protocol angle is MCP-compatible: publish `.well-known/asm`, or embed ASM under MCP Registry `server.json` `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`.

Important caveat: OpenRouter usage rank is a revealed-preference signal, not benchmark quality. The point is narrower: service selection should be reproducible before the API call happens.

Repo:
https://github.com/calebguo007/asm-spec
```

## Reddit / r/LocalLLaMA

Title:

```text
I built a CLI that picks OpenRouter models by cost and constraints
```

Body:

```text
I built ASM, a small CLI/protocol experiment for choosing AI services from structured metadata instead of manually reading pricing pages.

The practical demo is OpenRouter model selection:

    asm openrouter 'cheap coding model under $0.50 per 1M tokens'
    asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'

It builds ephemeral manifests from OpenRouter's public model metadata, applies hard constraints, ranks candidates, and can emit LiteLLM / Vercel AI SDK / LangChain snippets.

Caveats:
- OpenRouter's public model endpoint does not expose per-model latency or uptime.
- The usage-ranking signal is not benchmark quality.
- Free models dominate cost-first queries, so quality-sensitive use cases still need better benchmark metadata.

Repo:
https://github.com/calebguo007/asm-spec

I would especially like feedback on what metadata is missing for real model/API routing.
```

## X / Twitter

```text
I built ASM as a value router for AI services.

Try it on OpenRouter:

asm openrouter 'cheap coding model under $0.50 per 1M tokens'
asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'

It ranks models by structured pricing/provenance/usage metadata and emits router config.

MCP tells agents what services can do.
ASM tells agents what services are worth.

https://github.com/calebguo007/asm-spec
```

## LinkedIn

```text
I have been working on Agent Service Manifest (ASM), an open protocol and CLI for value-aware service selection in agent systems.

The core idea:

MCP tells agents what services can do.
ASM tells agents what services are worth.

The latest version is more practical: ASM can now rank live OpenRouter models from public metadata:

    asm openrouter 'cheap coding model under $0.50 per 1M tokens'

It can also emit router snippets:

    asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'

The goal is not to claim that any one quality metric is universally correct. The goal is to make pre-call service selection computable and reproducible: cost, constraints, provenance, verification, and eventually trust receipts.

Repo:
https://github.com/calebguo007/asm-spec
```

## 中文社区

Title:

```text
我做了一个 CLI：按价格、约束和元数据帮你选 OpenRouter 模型
```

Body:

```text
我最近在做 Agent Service Manifest（ASM），一开始它更像一个协议：给 AI service selection 定义 pricing、SLA、quality、provenance、verification 这些字段。

但我现在越来越确定，不能先让大家接受一个协议。要先让它变成一个有用工具。

所以最新版本先接了 OpenRouter：

    asm openrouter 'cheap coding model under $0.50 per 1M tokens'

它会从 OpenRouter 的公开 model metadata 生成临时 ASM manifest，然后按你的偏好和硬约束排序。也可以直接导出 router 配置：

    asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'

现在支持 LiteLLM / Vercel AI SDK / LangChain 片段。

我不想把它包装成“证明了哪个模型最好”。更准确的说法是：如果没有结构化 value metadata，agent 选服务这件事不可复现。ASM 是把这一步变成可计算、可审计的一次尝试。

Repo:
https://github.com/calebguo007/asm-spec

想听听大家真实选模型/API 时还缺哪些字段。
```

## Posting Order

1. Hacker News first only if the account is allowed to post Show HN.
2. If HN blocks Show HN posting, do not repost, do not use another account, and do not change the title to bypass the restriction. Move to LinkedIn and non-gated communities.
3. Reddit / r/LocalLLaMA should lead with the OpenRouter CLI utility, not the protocol paper, but only if the account is allowed to post.
4. If Reddit blocks posting because of karma/points/account-age rules, do not try to bypass it. Use comments in relevant existing threads, LinkedIn, X, GitHub issues, and Chinese developer communities first.
5. X / Twitter and LinkedIn can go immediately if HN or Reddit are unavailable.
6. Chinese community post can go in parallel if the audience is separate.

## HN Restriction Fallback

If Hacker News shows the temporary Show HN restriction for newer users:

- Do not try to bypass it.
- Spend time commenting naturally on HN before trying again later.
- Use the Reddit and LinkedIn drafts below as the primary first launch.
- If sharing on HN later, avoid a pure promotional pattern; contribute useful comments first, then post occasional project links when contextually relevant.

## Reddit Restriction Fallback

If Reddit or r/LocalLLaMA requires karma, points, or account age before posting:

- Do not repost from another account or ask for upvotes.
- Use Reddit in comment mode first: find existing threads about OpenRouter pricing, model routing, MCP servers, or provider selection, and leave a useful technical comment with the repo link only if it is directly relevant.
- Make LinkedIn the first public post.
- Use X / Twitter, GitHub issue follow-ups, V2EX, Zhihu, Juejin, or other communities where the account can post normally.
- Return to Reddit after the account has normal participation history.

## Accounts / Access

Do not share passwords or long-lived tokens. If Codex posts for you, use an already logged-in browser session. GitHub repo edits can use the existing `gh` authorization.
