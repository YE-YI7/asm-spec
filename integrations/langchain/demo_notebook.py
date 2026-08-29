"""Provider-free LangChain adapter demo."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from asm_protocol.integrations.langchain import (
    ASMReceiptCallback,
    ASMToolSelectorTool,
)


def main() -> None:
    tool = ASMToolSelectorTool()
    with TemporaryDirectory() as directory:
        callback = ASMReceiptCallback(output_dir=directory, verbose=False)
        message = tool.invoke(
            {
                "type": "tool_call",
                "id": "selection-demo",
                "name": "asm_tool_selector",
                "args": {
                    "task": "get public property data",
                    "taxonomy": "tool.data.real_estate",
                    "required_functions": "real_estate_data",
                    "require_agent_completable_setup": True,
                    "selection_profile": "legacy-0.5.2",
                },
            },
            config={"callbacks": [callback]},
        )
        print(message.content)
        print(json.dumps(message.artifact, indent=2, ensure_ascii=False))
        paths = list(Path(directory).glob("selection_*.json"))
        assert len(paths) == 1
        print(f"Persisted exact receipt: {paths[0]}")


if __name__ == "__main__":
    main()
