# ASM × AI Catalog (cross-protocol)

The [AI Catalog](https://github.com/Agent-Card/ai-catalog) is a cross-protocol standard (MCP, A2A, and others) for discovering heterogeneous AI artifacts. Like MCP Server Cards, its core schema covers *identification and discovery* — not the economic/eligibility metadata an agent needs to *choose among* several capable entries. ASM fills that layer here the same way it does for MCP: as metadata riding an official extension point, with no core-schema change.

## Where ASM fits: the `metadata` extension point

AI Catalog **ADR-0012** ("Extensibility via `metadata`", accepted) keeps the core entry schema *closed* and routes all custom properties into an optional `metadata` object — and states explicitly: *"Registries can define their own metadata schemas for entries they host without requiring changes to the core specification."* ASM's value/selection layer is a natural `metadata.asm` namespace.

```json
{
  "identifier": "urn:air:asm:amadeus/self-service-api@current",
  "displayName": "Amadeus Self-Service APIs",
  "mediaType": "application/asm+json",
  "url": "https://asm-spec.onrender.com/manifest/amadeus/self-service-api@current",
  "metadata": {
    "asm": {
      "asm_version": "0.3",
      "taxonomy": "tool.booking.travel",
      "invocation": { "interface": "rest_api", "reach": "cloud", "agent_operable": true },
      "operational": { "risk_class": "critical", "approval": "always" },
      "manifest_url": "https://asm-spec.onrender.com/manifest/amadeus/self-service-api@current"
    }
  }
}
```

## Convention: inline static, link mutable

We apply ASM's own inline-vs-link rule inside the catalog entry: `metadata.asm` carries the **static** eligibility/selection signals an agent gates on (taxonomy, invocation reach/operability, operational risk and approval), while `url` points at the full, **mutable** ASM manifest (pricing, quality, SLA) served at a canonical endpoint — so freshness has a single source and the catalog entry never drifts.

A runnable, source-linked example spanning the invocability spectrum (cloud API, local-device-only, critical-risk booking, keyless data) is in [`examples/ai-catalog/catalog.example.json`](../../examples/ai-catalog/catalog.example.json), generated from the live library by [`examples/ai-catalog/_build.py`](../../examples/ai-catalog/_build.py).

## Status and caveats

- **Not an official binding.** This is a demonstration that ASM's value layer fits the upstream standard's extension point cleanly; it is not a ratified ASM↔AI-Catalog mapping. No proposal has been filed with the AI Catalog project.
- **The spec is evolving.** At the time of writing, AI Catalog PRs are renaming `mediaType`→`type` and adopting `urn:air:` identifiers; the examples track the current ADR-0012 shape and will need updating as those land.
- **Why this matters.** The AI Catalog is more upstream than any single protocol's registry, and its `metadata` extension point is exactly where cross-protocol value/selection metadata could live without contention — a path worth watching as the standard matures.
