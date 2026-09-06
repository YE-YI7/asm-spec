# Selection data: Linear + Product Hunt first-pass audit

**Date:** 2026-08-31
**Scope:** first 10 entries shown in Linear's Agents directory
**Unit:** one public Linear integration listing
**Question:** can a human or agent compare eligible integrations before delegation?

`No` means the fact is not disclosed on the Linear listing. It does not mean the
underlying product lacks the capability.

## Rubric

- **Capability:** tasks and invocation trigger are clear.
- **Availability:** required product tier or availability boundary is clear.
- **Access:** permissions/data reach are explicit enough to assess before install.
- **Review:** human review or approval boundary is explicit.
- **Price:** a comparable price or pricing rule is present.
- **Evidence:** comparative quality, reliability, or SLA evidence is present.
- **Freshness:** listing version or last-verified date is present.
- **Machine card:** machine-readable selection metadata is linked or embedded.

## Sample

| Listing | Capability | Availability | Access | Review | Price | Evidence | Freshness | Machine card |
|---|---|---|---|---|---|---|---|---|
| [Codex](https://linear.app/integrations/codex) | Yes | Yes | Partial | Yes | No | No | No | No |
| [Cursor](https://linear.app/integrations/cursor) | Yes | Yes | Partial | Yes | No | No | No | No |
| [GitHub Copilot](https://linear.app/integrations/github-copilot) | Yes | Partial | Partial | Yes | No | No | No | No |
| [Factory](https://linear.app/integrations/factory) | Yes | No | Partial | Partial | No | No | No | No |
| [Sentry Agent](https://linear.app/integrations/sentry-agent) | Yes | No | Yes | No | No | No | No | No |
| [Devin](https://linear.app/integrations/devin) | Yes | No | Partial | Yes | No | No | No | No |
| [ChatPRD](https://linear.app/integrations/chatprd) | Yes | No | Partial | Partial | No | No | No | No |
| [Charlie](https://linear.app/integrations/charlie) | Yes | No | Partial | Yes | No | No | No | No |
| [cto.new](https://linear.app/integrations/cto-new) | Yes | No | Partial | Yes | No | No | No | No |
| [Coco by Cotera](https://linear.app/integrations/coco-by-cotera) | Yes | No | Partial | Partial | No | No | No | No |

## Findings

| Field | Sufficient disclosure | Finding |
|---|---:|---|
| Capability/trigger | 10/10 | strong human-readable discovery |
| Availability/tier | 2/10 | usually requires leaving Linear to learn eligibility |
| Permission/data boundary | 1/10 | Sentry is the only listing with detailed user-scoped OAuth requirements |
| Human review/approval | 6/10 | common for coding agents, inconsistent elsewhere |
| Comparable pricing | 0/10 | no listing supports cost comparison |
| Quality/reliability/SLA evidence | 0/10 | claims are descriptive, not comparative evidence |
| Version/last verified | 0/10 | selection facts cannot be freshness-checked |
| Machine-readable selection card | 0/10 | an agent cannot consume the listing as structured selection evidence |

## Product implication

Linear already solves discovery and human delegation. The first observed gap is
not another agent router. It is an optional, machine-readable selection profile
for availability, access boundary, review requirements, price, evidence, and
freshness, plus a conformance check for publishers.

This 10-listing sample validates a metadata-completeness problem only. It does
not prove that Linear, publishers, or users will adopt ASM, nor that these facts
improve task outcomes.

## Product Hunt comparison

**Scope:** purposive sample of eight Product Hunt pages that explicitly present
an API, MCP server, or CLI as usable by agents. This is a format comparison, not
a prevalence estimate or ranking of the products.

| Listing | Interface | Availability | Access | Review | Price | Evidence | Freshness | Machine card |
|---|---|---|---|---|---|---|---|---|
| [Product Hunt MCP](https://www.producthunt.com/products/product-hunt-mcp) | Yes | Yes | No | No | Yes | No | No | No |
| [Yavy](https://www.producthunt.com/products/yavy) | Yes | Partial | Yes | No | Partial | No | No | No |
| [Spanly](https://www.producthunt.com/products/spanly) | Yes | Yes | Partial | No | Yes | No | No | No |
| [agents-cli](https://www.producthunt.com/products/agents-cli) | Yes | Yes | Yes | Yes | Yes | No | No | No |
| [Open Computer Use](https://www.producthunt.com/products/open-computer-use) | Yes | Yes | Partial | Yes | Yes | No | No | No |
| [Keen Code](https://www.producthunt.com/products/keen-code-a-cli-coding-agent) | Yes | Yes | No | No | Yes | Partial | No | No |
| [rtrvr.ai](https://www.producthunt.com/products/rtrvr-ai) | Yes | No | Partial | No | No | No | No | No |
| [Mindcase](https://www.producthunt.com/products/mindcase) | Yes | Yes | No | No | Yes | No | No | No |

`Evidence` requires comparative quality, reliability, or SLA evidence. Reviews,
upvotes, and a maker's feature claims do not meet that bar. Keen Code is marked
partial because its maker reports a basic context-size benchmark and explicitly
describes its limitations.

| Field | Sufficient disclosure | Cross-directory observation |
|---|---:|---|
| Agent-operable interface | 8/8 | Product Hunt is strong at explaining API/MCP/CLI access |
| Availability/tier | 6/8 | stronger than Linear; `Free Options` alone remains ambiguous |
| Permission/data boundary | 2/8 | usually buried in comments or provider documentation |
| Human review/approval | 2/8 | present only when makers explain a deliberate human gate |
| Comparable pricing | 6/8 | much stronger than Linear, especially for free/open-source tools |
| Quality/reliability/SLA evidence | 0/8 | launch social proof is not selection-quality evidence |
| Version/last verified | 0/8 | launch recency does not verify current provider facts |
| Machine-readable selection card | 0/8 | pages remain human-readable launch material |

## Cross-directory conclusion

The missing fields differ by venue. Linear is strong on workflow and delegation;
Product Hunt is stronger on interface and commercial availability. Neither sample
supports fresh, machine-readable comparison of access boundaries, quality, and
evidence before an agent chooses a provider.

This supports testing a small selection-facts profile and publisher conformance
check. It does not support a universal score, a new registry, or a claim that ASM
improves real selection outcomes.

## Provider-document feasibility pilot

Three representative provider sources show that some missing facts are objective
and sourceable after leaving the directory:

| Provider | Objective facts found in provider source | Still unresolved for selection |
|---|---|---|
| [Spanly docs](https://spanly.com/docs/) | API-key auth, CLI/SDK/proxy/sidecar interfaces, credential-header redaction, 30/90/365-day retention, US/EU residency | no provider-independent reliability result or fact expiry |
| [Mindcase docs](https://docs.mindcase.co/authentication) | bearer auth, 60 requests/minute, explicit 401/402/429 semantics, SDK retries | no SLA or quality evidence; unit price varies by endpoint |
| [agents-cli repository](https://github.com/google/agents-cli) | supported commands, login path, local-versus-cloud boundary, explicit deploy targets | total execution cost depends on downstream Google services |

Result: interface, authentication, data boundary, rate limit, and some price facts
can be normalized without inventing a score. Quality, total cost, and freshness
cannot be inferred safely. Any prototype must retain `source`, `observed_at`, and
an explicit expiry/recheck policy instead of copying prose into a permanent catalog.

## Next test

1. Expand provider-document extraction to all 18 sampled listings.
2. Reject or flag facts that require subjective judgment or composite cost guesses.
3. Build paired selection tasks: directory descriptions versus normalized facts.
4. Seek external feedback only after the facts and evaluation are reproducible.
