# ASM LangChain integration

The packaged adapter exposes the canonical ASM selector as a LangChain tool. It
does not execute the selected service, enforce policy, or turn an approval flag
into authorization.

## Install

```bash
python -m pip install "asm-protocol[langchain]==0.6.0"
```

The compatibility checkout imports in this directory remain available, but new
code should use the packaged path:

```python
from asm_protocol.integrations.langchain import (
    ASMReceiptCallback,
    ASMToolSelectorTool,
)
```

## Structured result

LangChain models receive a short text summary. Hosts receive the full current
decision in `ToolMessage.artifact`. The v0.6 decision does not carry Selection
Receipt v0.1 because that frozen schema cannot represent the current cost model.

```python
from asm_protocol.integrations.langchain import ASMToolSelectorTool

tool = ASMToolSelectorTool()
message = tool.invoke({
    "type": "tool_call",
    "id": "selection-1",
    "name": "asm_tool_selector",
    "args": {
        "task": "get public property data",
        "taxonomy": "tool.data.real_estate",
        "required_functions": "real_estate_data",
        "require_agent_completable_setup": True,
    },
})

print(message.content)
decision = message.artifact
assert decision["selection_status"] == "selected"
```

The `task` field is audit context. The deterministic selector does not infer a
taxonomy or capabilities from natural language; callers must provide
`taxonomy` or `required_functions`.

If multiple eligible candidates do not have comparable cost facts, the default
result is `needs_cost_facts`. A caller may explicitly request
`fallback_policy="capability_breadth"`, but Selection Receipt v0.1 cannot encode
the v0.6 cost model, that fallback, or an explicit workload. The adapter returns
the structured decision without manufacturing a misleading receipt.

## Persist exact receipts

```python
from asm_protocol.integrations.langchain import ASMReceiptCallback

callback = ASMReceiptCallback(output_dir="./receipts")
legacy_tool_call = {
    **tool_call,
    "args": {**tool_call["args"], "selection_profile": "legacy-0.5.2"},
}
tool.invoke(legacy_tool_call, config={"callbacks": [callback]})
```

The callback persists the exact receipt carried by the tool artifact. It
ignores human-readable strings and malformed artifacts; it never reconstructs
a second receipt shape. The legacy profile exists only to reproduce the frozen
0.5.2/v0.1 contract; it is not the current cost-safe selector.

## Legacy checkout helpers

`asm_tools.py` still exposes the older registry/comparison helpers for checkout
users. They are not the canonical deterministic selection path and are not
shipped as the supported SDK integration.
