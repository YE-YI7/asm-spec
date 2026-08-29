"""Tests for the packaged LangChain selector and receipt callback."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("langchain_core")

from langchain_core.messages import ToolMessage

from asm_protocol.integrations.langchain import (
    ASMReceiptCallback,
    ASMToolSelectorTool,
)


def _tool_call(**arguments):
    return {
        "type": "tool_call",
        "id": "asm-selection-1",
        "name": "asm_tool_selector",
        "args": arguments,
    }


def test_default_refuses_to_guess_when_costs_are_not_comparable():
    tool = ASMToolSelectorTool()
    output = tool.invoke(
        {
            "task": "find and book a refundable flight",
            "taxonomy": "tool.booking.travel",
            "user_platform": "windows",
            "required_functions": "flight_search,flight_order_create",
        }
    )
    assert "Status: needs_cost_facts" in output
    assert "Selected tool:" not in output


def test_explicit_fallback_selects_but_does_not_issue_legacy_receipt():
    tool = ASMToolSelectorTool()
    output = tool.invoke(
        _tool_call(
            task="find and book a refundable flight",
            taxonomy="tool.booking.travel",
            user_platform="windows",
            required_functions="flight_search,flight_order_create",
            fallback_policy="capability_breadth",
        )
    )
    assert isinstance(output, ToolMessage)
    assert "Selected tool:" in output.content
    assert "risk_class: critical" in output.content
    assert "approval_required: True" in output.content
    assert output.artifact["selection_status"] == "selected"
    assert "receipt" not in output.artifact
    assert "frozen to selection_profile=legacy-0.5.2" in output.content


def test_current_tool_call_preserves_structured_decision_without_false_receipt():
    tool = ASMToolSelectorTool()
    output = tool.invoke(
        _tool_call(
            task="get property data",
            taxonomy="tool.data.real_estate",
            required_functions="real_estate_data",
            require_agent_completable_setup=True,
        )
    )
    assert isinstance(output, ToolMessage)
    assert output.artifact["selection_status"] == "selected"
    assert output.artifact["selected"]["display_name"] == "US Census Bureau Data API"
    assert "setup not agent-completable" in output.content
    assert "receipt" not in output.artifact
    assert "frozen to selection_profile=legacy-0.5.2" in output.content


def test_receipt_callback_persists_exact_tool_artifact(tmp_path):
    callback = ASMReceiptCallback(output_dir=str(tmp_path), verbose=False)
    tool = ASMToolSelectorTool()
    output = tool.invoke(
        _tool_call(
            task="get property data",
            taxonomy="tool.data.real_estate",
            required_functions="real_estate_data",
            require_agent_completable_setup=True,
            selection_profile="legacy-0.5.2",
        )
    )
    callback.on_tool_end(output)
    paths = list(tmp_path.glob("selection_*.json"))
    assert len(paths) == 1
    assert json.loads(paths[0].read_text(encoding="utf-8")) == output.artifact["receipt"]


def test_receipt_callback_ignores_human_text_and_malformed_artifacts(tmp_path):
    callback = ASMReceiptCallback(output_dir=str(tmp_path), verbose=False)
    callback.on_tool_end("Selected tool: not structured evidence")
    callback.on_tool_end(("content", {"receipt": {"receipt_type": "selection"}}))
    assert list(tmp_path.iterdir()) == []


def test_args_schema_exposes_cost_and_fallback_boundaries():
    schema = ASMToolSelectorTool().args_schema.model_json_schema()
    assert {
        "task",
        "taxonomy",
        "monthly_units",
        "amortization_months",
        "fallback_policy",
        "selection_profile",
    } <= set(schema["properties"])
