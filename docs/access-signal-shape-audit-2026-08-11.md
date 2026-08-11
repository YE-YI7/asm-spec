# Access-signal shape audit — 30-tool ASM library

> Run date: 2026-08-11
> Question: does the discovery projection used in ai-catalog#83 preserve the
> pricing and free-tier facts needed for agent selection?
> Reproduce: `python experiments/access_signal_shape_audit.py --pretty`

## Dataset and grain

- 30 committed manifests under `library/**/*.asm.json`
- one row / manifest per service
- source verification dates are 2026-06-08 or 2026-06-09
- no live pricing pages were re-scraped for this audit

The audit therefore tests **shape coverage of the committed evidence**, not
whether every vendor's current price is still correct.

## Results

| Check | Result | Decision impact |
|---|---:|---|
| Manifests marked with a free tier | 22 / 30 | Confirms the coarse free/freemium gate has broad coverage. |
| Free-tier entries with any human-readable detail | 8 / 22 | Fourteen free-tier signals have no allowance detail in the pricing object. |
| Machine-readable free-tier rule sets | 0 / 22 | The current boolean projection cannot express caps, reset windows, scopes, or compound allowances. |
| Services with multiple positive price dimensions | 1 / 30 | Perplexity has separate input/output prices; selecting one cheapest scalar loses a billing dimension. |
| Text-heuristic candidates for runtime/caller-specific resolution | 6 / 30 | These require source review; this is a triage set, not six verified personalized contracts. |
| Known coarse-tier conflict | 1 / 30 | ATTOM is emitted as `free`, while its manifest says the free access is a 30-day trial and production pricing is sales-led. |

Current derived tier distribution remains 17 free, 5 freemium, 4 paid,
2 subscription, and 2 negotiated. This reproduces the earlier 17 / 5 / 6 / 2
summary when paid and subscription are combined.

## Findings

### High — a boolean `freeTier` is insufficient

Twenty-two manifests advertise free access, but only eight carry any
`pricing.free_tier` description and none carry machine-readable arrays of
allowance rules. A discovery client cannot distinguish, for example, a daily
request cap from a monthly storage cap or a caller-specific entitlement.

This supports the ai-catalog#83 suggestion to represent free-tier rules as an
array. The candidate extension keeps `freeTierRules` as an array even when the
only available rule is currently a human-readable description, so structured
rules can replace descriptions incrementally without another shape change.

### Medium — one scalar price is already lossy

The legacy catalog projection selects the cheapest positive billing dimension.
That drops one of Perplexity's input/output token dimensions. The candidate
extension emits `priceEchoes[]`, retaining every positive dimension and its
verification timestamp. Echoes remain explicitly non-authoritative.

### Medium — authenticated pricing needs a reference, not a guessed number

Six manifests contain text suggesting plan-, tier-, API-, sales-, model-, or
publisher-dependent terms. This regex-derived set is only a review queue. It
does show why a schema needs an optional authenticated `pricingResolver`
reference even though the current 30 manifests do not yet populate one.

### High — coarse tier derivation has a real contradiction

`attom/property-api@current` currently derives as `free` because it has a
`free_tier` payment method and no positive public price. Its own provenance says
the free access is a 30-day trial and production pricing is paid via sales.
Selection based only on the derived tier could therefore admit a service an
autonomous production run cannot purchase.

The fix should be source data or an explicit access override, not a prose
heuristic in the selector.

## Candidate extension

The candidate schema is `schema/asm-ai-catalog-access-v0.1.schema.json` under
the temporary vendor namespace `io.github.ye-yi7.asm.access`. It provides:

- a coarse `tier` filter;
- all declared payment `mechanisms`;
- non-authoritative `priceEchoes[]`;
- `freeTierRules[]` for compound caps and reset windows;
- an optional authenticated `pricingResolver` reference;
- an authoritative `pricingUrl` fallback.

All 30 manifests produce schema-valid candidate objects in the automated test.
Runtime settlement amounts remain in the payment challenge / receipt layer,
outside discovery.

## Recommendation

1. Share the measured gaps in ai-catalog#83; do not claim caller-specific
   pricing for all six review candidates.
2. Keep the namespace vendor-scoped until the WG chooses a neutral extension
   key.
3. Do not mutate ASM v0.3 solely for this discussion. First replace prose free
   allowances with verified structured rules and add explicit resolver
   references where a provider actually exposes one.
4. Migrate the live AI Catalog projection from its older flat `metadata` shape
   to the current AI Catalog `extensions` field only after compatibility tests
   are added; that migration is distinct from this data-shape audit.

## Confidence

**Ready to share with caveats.** Counts and loss checks are deterministic over
the committed 30-manifest library. Vendor price freshness and the six resolver
candidates require a separate live-source verification pass.
