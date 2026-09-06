# Web-search replay profile

Observed: 2026-09-05. Status: provider-declared API shapes converted into
minimal, synthetic replay fixtures. No authenticated call or quality claim.

| Candidate operation/mode | Source facts retained | What ASM refuses to infer |
|---|---|---|
| Tavily Search, API, `basic`/auto-resolved mode | response has ranked `results`, `request_id`, selected `auto_parameters`, and `usage.credits`; basic/fast/ultra-fast and advanced can consume different credits | credits are not dollars without the caller's account plan; a result score is not cross-provider quality |
| Exa Search, API, resolved search type | response has `results`, `requestId`, `resolvedSearchType`, `searchTime`, and optional `costDollars.total` | `costDollars` is retained as provider estimate, not settled billing; text/summary extras are not compared with URL/snippet-only modes |
| Firecrawl Search, API, web source without scrape formats | response has `success`, `data.web`, job `id`, warning, and `creditsUsed`; scrape options can add full content and different consumption | credits are not dollars; search-only output cannot be compared to search-plus-scrape as the same operation |

Sources:

- https://docs.tavily.com/documentation/api-reference/endpoint/search
- https://exa.ai/docs/reference/search
- https://docs.firecrawl.dev/api-reference/endpoint/search

The fixture payloads in `examples/contracts/search/providers/` contain no key,
real query, customer data, or claimed live measurement. They test normalization
and accounting boundaries only. Provider versions and pricing must be refreshed
before any live comparison.
