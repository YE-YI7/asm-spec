# RFC: Operational Constraints for Pre-call Agent Service Selection

**Status**: Draft  
**Target version**: ASM v0.4  
**Authors**: Yi Guo (ASM)  
**Motivation source**: MCP community feedback that pricing, quotas, approvals,
and risk often act as the same operational boundary in agent systems.

## 1. Summary

ASM v0.3 makes service value metadata computable: pricing, quality, SLA,
provenance, verification, payment, and receipts. The next step is to make the
pre-call operational envelope explicit.

The core claim:

> MCP describes what a tool can do. ASM describes the operational envelope
> around using it before the call.

In practice, cost, rate limits, quotas, approval rules, side effects, and risk
controls travel together. A client deciding whether to invoke a tool should not
only ask "what does this cost?" It should also ask:

- Is this call inside the user's spend cap?
- Is this call inside the provider's quota and rate-limit envelope?
- Does this action require human approval because of cost, side effects, or
  risk class?
- Does this tool have destructive, external, or persistent side effects?
- Is a receipt required so the post-call result can update Trust Delta?

This RFC proposes a small `operational_constraints` object that publishers can
embed in ASM manifests or MCP Registry `server.json` `_meta` blocks without
requiring MCP core changes.

## 2. Non-goals

- ASM does not become a policy engine. Clients enforce local policy.
- ASM does not decide whether a tool is safe. It exposes metadata that clients,
  registries, and hosts can use for local decisions.
- ASM does not replace MCP `ToolAnnotations`. It complements them with economic
  and operational fields that are useful before invocation.
- v0.4 should not require complete coverage. Partial operational metadata is
  acceptable if provenance is clear.

## 3. Proposed manifest field

Draft field:

```json
{
  "operational_constraints": {
    "risk_class": "medium",
    "side_effects": ["external_api_call", "persistent_state"],
    "approval": {
      "required": "conditional",
      "conditions": [
        "estimated_cost_usd > 1.00",
        "writes_external_state == true"
      ],
      "human_readable": "Require approval for paid calls over $1 or writes to external systems."
    },
    "spend_caps": {
      "per_call_usd": 1.0,
      "per_day_usd": 25.0,
      "currency": "USD"
    },
    "quotas": [
      {
        "dimension": "request",
        "limit": 10000,
        "period": "monthly",
        "scope": "account"
      }
    ],
    "rate_limits": [
      {
        "dimension": "request",
        "limit": 60,
        "period": "minute",
        "scope": "account",
        "burst": 10
      }
    ],
    "receipt_required": true,
    "policy_notes": "Publisher-declared limits. Consumer policy remains authoritative."
  }
}
```

## 4. Field semantics

| Field | Type | Purpose |
|---|---|---|
| `risk_class` | enum | Coarse operational risk: `low`, `medium`, `high`, `critical` |
| `side_effects` | array | Declared effects such as `read_only`, `external_api_call`, `persistent_state`, `financial_charge`, `sends_message`, `executes_code`, `network_access` |
| `approval.required` | enum | `never`, `conditional`, or `always` |
| `approval.conditions` | array | Human-readable or policy-language conditions that trigger approval |
| `spend_caps` | object | Publisher or consumer-advised maximums per call/day/month |
| `quotas` | array | Provider quota envelope, usually monthly or daily |
| `rate_limits` | array | Provider request-rate envelope, usually per second/minute/hour |
| `receipt_required` | boolean | Whether the client should expect a post-call receipt before updating trust |
| `policy_notes` | string | Caveats and local policy interpretation notes |

## 5. Relationship to existing ASM fields

`operational_constraints` does not replace existing fields:

- `pricing` declares how cost is computed.
- `sla.rate_limit` can remain a compact human-readable field for backward
  compatibility.
- `payment` declares auth, signup, and receipt endpoints.
- `verification` declares how receipts or claims can be checked.
- `operational_constraints` declares the pre-call guardrails that clients can
  reason over before invocation.

Recommended v0.4 guidance:

- If structured `rate_limits[]` is present, clients SHOULD prefer it over
  `sla.rate_limit`.
- If `receipt_required` is true, clients SHOULD check `payment.receipt_endpoint`
  or `payment.receipt_envelope_version`.
- If `approval.required` is `always` or a condition evaluates true, clients
  SHOULD pause before invocation.
- If `risk_class` is `high` or `critical`, clients SHOULD require an explicit
  local policy decision even if the provider does not require approval.

## 6. MCP Registry embedding

Publishers can embed this draft field today under the existing ASM `_meta`
location:

```json
{
  "_meta": {
    "io.modelcontextprotocol.registry/publisher-provided": {
      "asm": {
        "asm_version": "0.3",
        "service_id": "example/search@1.0",
        "taxonomy": "tool.data.search",
        "operational_constraints": {
          "risk_class": "medium",
          "approval": {
            "required": "conditional",
            "conditions": ["estimated_cost_usd > 1.00"]
          },
          "receipt_required": true
        }
      }
    }
  }
}
```

The v0.3.x schema accepts this field as experimental producer-side metadata so
early integrations can validate today. The v0.4 RFC process will decide whether
the exact field names and enums become stable.

## 7. Open questions

1. Should `approval.conditions` be only human-readable strings in v0.4, or
   should ASM define a small policy expression grammar?
2. Should `risk_class` be publisher-declared, registry-curated, or both?
3. Should `side_effects` align exactly with MCP ToolAnnotations hints, or stay
   ASM-specific to cover economic/operational effects?
4. Should `spend_caps` be publisher-declared limits, consumer policy limits, or
   both with separate namespaces?
5. Should receipt requirements be advisory, or should a client be able to treat
   missing receipts as a hard failure?

## 8. Acceptance criteria for v0.4

- At least two reference integrations from different service categories include
  `operational_constraints`.
- At least one MCP `server.json` example embeds the field under
  `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`.
- The validator treats the field as forward-compatible metadata and preserves it
  during extraction.
- Documentation clearly states that ASM exposes policy inputs but does not
  enforce local policy.

## 9. Adoption wedge

The adoption target is producer-side, not registry-side:

1. MCP server authors add optional `operational_constraints`.
2. Validators confirm the metadata is extractable and schema-compatible.
3. Reference integrations accumulate in this repo.
4. Aggregators revisit indexing once publisher coverage exists.

This directly addresses the current registry adoption gate: sparse coverage.
The first useful milestone is not a registry default ranking. It is three to
five producer-owned ASM blocks that make cost, rate, approval, and risk visible
before invocation.
