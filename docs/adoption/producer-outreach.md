# Producer-side Outreach Plan

Registry feedback made the adoption gate clear: aggregators are interested in
ASM value facets, but they need publisher coverage first. This outreach plan
targets MCP server authors and small service producers.

## Ask

Do not ask maintainers to "adopt ASM" in the abstract. Ask whether they would
review a minimal PR that adds optional publisher-provided metadata under
`server.json` `_meta`.

## Primary message

```md
Hi - I am working on Agent Service Manifest (ASM), an optional value-metadata
layer for MCP servers.

I am not asking you to change runtime behaviour. The small integration would be
one publisher-provided metadata block under MCP Registry `server.json` `_meta`:

`_meta.io.modelcontextprotocol.registry/publisher-provided.asm`

It would expose pre-call metadata that clients and registries can reason over:
pricing/free-tier assumptions, quotas/rate limits, approval boundaries, risk
class, provenance, and whether receipts are supported.

Example:
https://github.com/calebguo007/asm-spec/blob/main/examples/mcp-server-json/operational-envelope-with-asm.server.json

Producer guide:
https://github.com/calebguo007/asm-spec/blob/main/docs/adoption/producer-guide.md

Would you be open to a minimal PR adding an optional ASM block to this server's
metadata/docs? It would not affect MCP invocation and can be removed if it does
not fit your project.
```

## If the maintainer asks why

```md
The practical reason is pre-call control. Agents often need to know whether a
tool call is within budget, quota, rate-limit, approval, or risk boundaries
before invoking it. Today those constraints are usually buried in README text,
pricing pages, or deployment assumptions.

ASM makes those fields machine-readable while leaving enforcement to the client
or host.
```

## If the maintainer says registries should do this

```md
I agree registries are the right place to index it eventually. The feedback from
registry maintainers so far is that value facets become useful once publishers
start exposing coverage. That is why I am starting with producer-owned metadata
blocks instead of asking registries to infer or curate the data first.
```

## Good first targets

Prefer projects where one small metadata PR can be reviewed quickly:

- MCP servers with a checked-in `server.json`, `mcp.json`, or registry metadata.
- Paid API wrappers where pricing/rate limits are already documented.
- Browser/search/scraping servers where rate limits and risk are operationally
  meaningful.
- Small active repos with recent maintainer activity.

Avoid first:

- Core MCP repos.
- Large companies unless there is an obvious maintainer contact.
- Projects with no issues/PRs enabled.
- Projects where pricing is impossible to infer from public docs.

## Success criteria

Seven-day target:

- 10 producer-side issues opened or PRs offered.
- 3 maintainers reply.
- 2 minimal PRs accepted or under review.
- 1 second reference integration outside `tool.code.orchestration`.

The target is coverage, not stars.

## Candidate target list

Generated from GitHub repository search on 2026-05-25. Prioritise active
producer-side MCP servers where cost, quota, approval, or operational risk is
visible enough to make a small ASM block meaningful.

| Repo | Why it fits | First ask |
|---|---|---|
| `browserbase/mcp-server-browserbase` | Browser automation over a paid/hosted service; rate, spend, and approval boundaries matter. | Offer a PR adding operational envelope metadata for browser sessions. |
| `karanb192/reddit-mcp-buddy` | Social-data MCP; API limits and account/risk boundaries are natural metadata. | Ask whether quotas/rate limits can be represented under `_meta...asm`. |
| `kaael1/mcp-power-automate` | Automation server with side effects; approval boundaries are central. | Offer a PR focused on `risk_class`, `side_effects`, and approval conditions. |
| `XPOZpublic/xpoz-mcp` | Social search API wrapper; indexed data, likely quotas, and external API calls. | Ask for pricing/rate/provenance metadata shape feedback. |
| `danielsmithdevelopment/ClawQL` | API gateway over OpenAPI/Swagger specs; many upstream operations and operational constraints. | Offer an example ASM block for one bundled provider. |
| `JDeun/unified-search-mcp-server` | Search MCP across web/scholar/YouTube; rate limits and external calls are obvious. | Offer low-friction `_meta` metadata PR. |
| `arthurle3210/swapi-pilot-solidworks-mcp` | Domain-specific API-doc search server with clear capability boundary. | Ask for a minimal self-reported value metadata block. |
| `sahajamit/VidSnatch` | YouTube toolkit with download/trim side effects and quota-sensitive operations. | Focus on side effects and approval/risk metadata. |
| `pr1m8/pyfetcher` | Fetch/scrape/extract/download MCP; operational risk and rate limits are first-class. | Offer operational envelope PR. |
| `CaullenOmdahl/youtube-music-mcp-server` | Playlist/search management can mutate external state. | Ask whether approval and side-effect fields fit. |

Avoid opening all issues at once. Start with two or three highest-fit repos,
preferably with one PR offer and one discussion issue, then wait for signal.
