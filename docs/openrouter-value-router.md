# OpenRouter Value Router

ASM's first practical adoption wedge is model/provider selection.

Instead of asking every service publisher to write an ASM manifest first, the OpenRouter adapter converts public OpenRouter model metadata into ephemeral ASM manifests and runs the normal ASM scorer over them.

## Why This Exists

Protocol adoption is slow. A useful router is immediate.

OpenRouter already exposes model IDs, pricing, context windows, modalities, and provider metadata. ASM adds the missing decision step: turn that metadata into a reproducible ranking for a user preference such as cheap, high quality, low latency, or reliable.

## Try It

```bash
pip install -e .
asm openrouter 'cheap coding model under $0.50 per 1M tokens'
```

Export a router config:

```bash
asm openrouter route --format litellm 'cheap coding model under $0.50 per 1M tokens'
asm openrouter route --format vercel-ai-sdk 'high quality reasoning model'
asm openrouter route --format langchain 'cheap reliable chat model'
```

Machine-readable output:

```bash
asm openrouter --format json 'best value model for long-context summarization'
```

## What ASM Uses

The adapter maps OpenRouter metadata into ASM fields:

| OpenRouter source | ASM field |
|---|---|
| model id/name | `service_id`, `display_name` |
| prompt/completion pricing | `pricing.billing_dimensions` |
| context length/modalities | `capabilities` |
| cached OpenRouter rankings | `quality.metrics[openrouter_usage_signal]` |
| fetch timestamp/source URL | `provenance` |

The OpenRouter rankings signal is a revealed-preference usage signal, not a benchmark-quality claim. ASM reports it as such and keeps provenance attached.

## Caveats

- OpenRouter `/api/v1/models` does not expose per-model latency or uptime, so latency constraints are reported and ignored unless `--strict-latency` is set.
- Free models often dominate cost-first queries. Use quality-oriented prompts when that is not desired.
- Usage rank is not quality. It is useful for routing stress tests and practical defaults, not for claiming one model is objectively better.
- Prices can change. Live API output is intentionally treated as ephemeral metadata.

## Design Point

This makes ASM an intermediate representation:

```text
OpenRouter metadata -> ephemeral ASM manifests -> TOPSIS value ranking -> router config
```

That is the adoption path: users get a useful model selector today, while ASM remains the portable value metadata layer underneath.
