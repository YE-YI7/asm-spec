# ASM v0.6.0 release and migration notes

ASM v0.6.0 makes the deterministic selection boundary explicit and packages
the first-party LangChain adapter. It is a behavior-changing minor release for
callers that relied on task-text inference, scalar cost shortcuts, or automatic
Selection Receipt v0.1 emission.

## What changed

- `src/asm_protocol/` is the canonical selector SDK and the package/selector
  version has one source of truth.
- Task text is audit context. A request without `taxonomy` or
  `required_functions` returns `under_specified`.
- Metered, one-time, multi-currency, and prose-only free-tier pricing is exposed
  as `known`, `partial`, or `unknown`. The current selector returns
  `needs_cost_facts` when several eligible candidates cannot be compared.
- `fallback_policy="capability_breadth"` is explicit; it is never silently
  applied.
- Selection Receipt v0.1 remains frozen to the explicit
  `selection_profile="legacy-0.5.2"` compatibility path. Current v0.6 cost
  decisions cannot emit it.
- `asm_protocol.integrations.langchain` is included in the wheel. The tool keeps
  the complete decision in `ToolMessage.artifact`; its callback persists only
  the exact receipt artifact and never reconstructs evidence from prose.
- The DeepSeek Harness adapter defaults to the current receipt-free decision.
  Its historical receipt behavior requires `legacyReceipt: true`.
- CI installs the LangChain extra, so adapter tests cannot silently skip.

## Migration

Install the release and the extras actually used by the host:

```bash
python -m pip install --upgrade "asm-protocol==0.6.0"
python -m pip install --upgrade "asm-protocol[mcp,langchain]==0.6.0"
```

Callers should:

1. provide `taxonomy` or `required_functions` instead of expecting task-text
   classification;
2. provide workload facts for metered pricing, or handle
   `selection_status="needs_cost_facts"`;
3. request `fallback_policy="capability_breadth"` only when that policy is
   acceptable; and
4. consume the structured v0.6 decision instead of requesting receipt v0.1.

Existing consumers that must reproduce the historical Selection Receipt v0.1
fixture may temporarily use:

```python
select(
    task="audit text",
    taxonomy="tool.data.search",
    selection_profile="legacy-0.5.2",
    receipt=True,
)
```

The legacy profile rejects workload and fallback inputs. Its scalar costs are a
compatibility projection, not v0.6 cost-safe estimates.

## Verification at the release commit

- Python 3.12: 213 tests passed (211 selector-hardening tests plus release
  pin-alignment and adoption-example readiness regression tests).
- DeepSeek Harness adapter: 8 tests passed and `npm pack --dry-run` succeeded.
- The built wheel contains `asm_protocol.integrations.langchain`.
- A clean wheel installation with LangChain Core 1.6.1 passed current and legacy
  smoke tests.
- GitHub CI for the selector-hardening merge passed all six checks.
- Independent OpenCode MiMo review returned `RELEASE` before merge.

These are implementation and packaging receipts. They are not external runtime
adoption or commercial validation.
