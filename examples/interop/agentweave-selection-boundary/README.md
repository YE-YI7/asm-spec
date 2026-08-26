# AgentWeave selection-boundary fixture

This synthetic fixture tests one narrow handoff between ASM and AgentWeave:

```text
two unchanged MCP descriptors
        +
two external ASM Selection Facts sidecars
        +
one explicit structured constraint
        ↓
one selected service + unsigned Selection Receipt
        ↓
one unchanged MCP descriptor becomes model-visible
```

It was prepared outside AgentWeave for review, following the maintainer's
request in the MCP service-discovery discussion. It does not modify MCP core
fields or AgentWeave, and it is not an AgentWeave adoption claim.

## What is pinned

- [`mcp-tools.json`](mcp-tools.json) contains exactly two plain MCP
  `tools/list`-style descriptors.
- [`sidecars/`](sidecars/) contains exactly two synthetic ASM v0.3 manifests.
  Each sidecar carries a provisional namespaced binding to one descriptor; this
  is fixture encoding, not an accepted AgentWeave or ASM core field.
- [`task-constraint.json`](task-constraint.json) carries the auditable task text
  and the structured taxonomy, reach, platform, function, setup, and approval
  constraints used by the deterministic selector. ASM does **not** infer these
  constraints from the task sentence.
- [`selection-receipt.json`](selection-receipt.json) pins the full candidate set,
  exact sidecar digests, structured request, chosen service, alternative, policy
  facts, and selector version.
- [`fixture-result.json`](fixture-result.json) pins the source-catalog digest,
  exact selected descriptor, filtered descriptor, and the boundary with
  AgentWeave's native routing-provenance record.

Both candidates satisfy the structured capability constraints. Their declared
costs are unambiguous USD monthly subscriptions ($4 and $9), so ASM selects the
$4 candidate without inventing request volume, free-tier allowance, or a
fallback policy. Selection Receipt v0.1 cannot encode workload or cost
uncertainty; this fixture therefore must not be generalized to metered or
free-tier comparisons.

## Reproduce

From the ASM repository root:

```bash
python3 tools/build_agentweave_selection_fixture.py --check
python3 -m pytest tools/asm-gen/test_agentweave_selection_fixture.py
```

Use `--write` only after intentionally changing a source descriptor, sidecar,
constraint, or selector result.

## Responsibility boundary

The ASM receipt answers the pre-inference question: which service was selected,
from which exact Selection Facts, under which explicit constraints?

AgentWeave's native `ToolRoutingProvenance` remains responsible for its own
policy and router drops, the tools actually shown to the model, the model call,
authorization, execution, recovery, and stage telemetry. This external fixture
does not fabricate that native record. It references AgentWeave commit
`1f2e9c88c6e85dc072e17fb06ff67038c4d45687`, where the MCP example and native
provenance implementation were inspected.

The receipt is unsigned and does not attest that either synthetic price is true.
`approval_required: true` is a policy input, not authorization. The fixture does
not call either tool, create an issue, perform a payment, or prove production
interoperability.

## Review questions

1. Is the provisional sidecar-to-MCP-descriptor binding sufficient and placed at
   the right boundary?
2. Does the Selection Receipt contain enough pre-inference provenance for an
   AgentWeave consumer to inspect and reproduce this decision?
3. What minimal reference should AgentWeave's native provenance carry back to
   this receipt: its digest, URI plus digest, or neither?

Upstream context:

- [AgentWeave MCP routing example](https://github.com/sauravsingla/agentweave/blob/1f2e9c88c6e85dc072e17fb06ff67038c4d45687/examples/mcp_tool_routing.py)
- [AgentWeave native routing provenance](https://github.com/sauravsingla/agentweave/blob/1f2e9c88c6e85dc072e17fb06ff67038c4d45687/agentweave_security/routing_provenance.py)
- [MCP service-discovery discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/69#discussioncomment-18156563)
