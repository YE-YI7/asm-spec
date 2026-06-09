# Productization and Distribution Plan

ASM should not be sold as "please adopt my schema." It should be distributed as a tool-selection layer that agent builders can use immediately.

## Current Wedge

The `library/` directory is the product surface:

```text
task -> eligible tools -> policy gates -> value ranking -> selected tool
```

The important gates are not only price or quality. For agent use, the first questions are:

- Can this agent actually invoke the tool from its runtime?
- Is automated use allowed?
- Does the action send a message, mutate state, execute code, or spend money?
- Does the tool keep, train on, or lock in user data?
- Does the action need approval before the call?

This is why booking/travel and communication are stronger demos than another model-router result. They make risk and approval visible.

## Distribution Tracks

| Track | What ships | Why it matters |
|---|---|---|
| Hosted selector API | `POST /select` over the `library/` manifests | Lets agent apps use ASM without vendoring the repo. |
| Python package | `asm select --library ...` plus importable selector | Makes CLI/framework integration low-friction. |
| MCP server | `asm-selector` MCP server exposing `select_tool` | Lets Claude Desktop/Cursor/agent hosts call ASM like any other tool. |
| LangChain/LangGraph adapter | Tool/router wrapper returning selected service + policy warnings | Meets builders where they already compose agents. |
| Registry/aggregator import | JSON feed + `_meta...asm` extraction | Lets MCP aggregators index fields once producer coverage exists. |

## Minimum Hosted API

```http
POST /select
Content-Type: application/json

{
  "task": "find and book a refundable flight",
  "taxonomy": "tool.booking.travel",
  "agent_reach": "cloud",
  "user_platform": "windows",
  "required_functions": ["flight_search", "flight_order_create"],
  "policy": {
    "require_approval_for": ["financial_charge", "sends_message", "executes_code"]
  }
}
```

Response:

```json
{
  "selected": "duffel/flights-api@current",
  "approval_required": true,
  "risk_class": "critical",
  "reason": "Eligible cloud API with flight_order_create; booking/payment requires approval.",
  "rejected": [
    {"service": "Calendly API", "reason": "missing required: flight_search, flight_order_create"}
  ]
}
```

## What To Build Next

1. Add `library_select.py` as an importable module, not only a demo script.
2. Add `asm select "task..." --taxonomy ... --json`.
3. Add an MCP server wrapper around `select_tool`.
4. Publish a hosted read-only selector on Vercel/Railway using the checked-in library.
5. Add a weekly coverage report: domains, tools, unknown governance fields, high-risk approval boundaries.

## Adoption Rule

Do not ask external projects to maintain ASM until the selector is useful without them.

The order is:

1. Curated library proves the selection shape.
2. Hosted selector gives agent builders immediate utility.
3. Framework adapters create distribution.
4. Producers add first-party ASM because appearing in selectors becomes valuable.
