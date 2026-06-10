"""Tests for the LangChain adapter (ASMToolSelectorTool). Skipped if langchain-core absent."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("langchain_core")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations" / "langchain"))

from asm_tools import ASMToolSelectorTool  # noqa: E402


def test_selector_tool_booking_flow():
    tool = ASMToolSelectorTool()
    out = tool._run(
        task="find and book a refundable flight",
        taxonomy="tool.booking.travel",
        user_platform="windows",
        required_functions="flight_search,flight_order_create",
    )
    assert "Amadeus" in out
    assert "risk_class: critical" in out
    assert "approval_required: True" in out


def test_selector_tool_setup_gate():
    tool = ASMToolSelectorTool()
    out = tool._run(
        task="get property data",
        taxonomy="tool.data.real_estate",
        required_functions="real_estate_data",
        require_agent_completable_setup=True,
    )
    assert "US Census Bureau Data API" in out
    assert "setup not agent-completable" in out


def test_selector_tool_is_valid_langchain_tool():
    tool = ASMToolSelectorTool()
    assert tool.name == "asm_tool_selector"
    schema = tool.args_schema.model_json_schema()
    assert "task" in schema["properties"]
    # invoke via the LangChain interface, not just _run
    out = tool.invoke({"task": "store a study plan with daily reminders",
                       "taxonomy": "tool.productivity.task_management",
                       "user_platform": "windows",
                       "required_functions": "reminders,recurring_tasks"})
    assert "Selected tool:" in out
