# ASM × AI Catalog (cross-protocol)

The [AI Catalog](https://github.com/Agent-Card/ai-catalog) discovers heterogeneous
AI artifacts across MCP, A2A, skills, datasets, and other formats. Its core tells
a client what an artifact is and where to fetch it. ASM adds the separate facts
an agent needs before choosing among otherwise capable services.

## Current extension mapping

The public AI Catalog specification checked on 2026-08-16 exposes an optional
`extensions` object on each catalog entry. Every extension key must be a valid
URL or reverse-DNS string. This repository uses the provisional namespace
`io.github.ye-yi7.asm.selection`:

```json
{
  "identifier": "urn:air:github.com:ye-yi7:asm:amadeus:self-service-api",
  "displayName": "Amadeus Self-Service APIs",
  "type": "application/asm+json",
  "version": "current",
  "url": "https://asm-spec.onrender.com/manifest/amadeus/self-service-api@current",
  "extensions": {
    "io.github.ye-yi7.asm.selection": {
      "asm_version": "0.3",
      "taxonomy": "tool.booking.travel",
      "invocation": {
        "interface": "rest_api",
        "reach": "cloud",
        "agent_operable": true
      },
      "operational": {
        "risk_class": "critical",
        "approval": "always"
      },
      "manifest_url": "https://asm-spec.onrender.com/manifest/amadeus/self-service-api@current"
    }
  }
}
```

This is an illustrative, unratified mapping. AI Catalog issue #83 remains the
place where discovery-time access and monetization signals are being discussed;
the example above must not be described as an accepted upstream namespace.

## Inline stable facts, resolve mutable facts

The entry may carry compact eligibility signals needed for coarse filtering.
Mutable or caller-specific price, allowance, quality, and SLA data should keep
source and retrieval timestamps and be resolved from the linked ASM snapshot or
the runtime provider. A discovery-time scalar is never the final payable amount.

The generated example is
[`examples/ai-catalog/catalog.example.json`](../../examples/ai-catalog/catalog.example.json),
built by [`examples/ai-catalog/_build.py`](../../examples/ai-catalog/_build.py).

## Boundary

- AI Catalog identifies and locates artifacts.
- ASM normalizes selection facts, applies local policy, and emits a selection receipt.
- MPP, x402, Stripe, ACP, or UCP owns its runtime quote/payment/commerce receipt.
- Observed outcome evidence remains a separate artifact linked by subject/version/digest.
