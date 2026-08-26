from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.build_agentweave_selection_fixture import (
    FIXTURE,
    ROOT,
    build_fixture,
    render,
    source_documents,
)


def test_agentweave_fixture_is_schema_valid_and_bounded() -> None:
    receipt, result = build_fixture()
    schema = json.loads(
        (ROOT / "schema" / "selection-receipt-v0.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(receipt)

    assert len(receipt["evidence"]) == 2
    assert result["routing_decision"]["selected_service_id"] == (
        "agentweave-fixture/tracker-standard@1.0.0"
    )
    assert result["routing_decision"]["selected_mcp_tool_name"] == (
        "tracker_standard_create_issue"
    )
    assert len(result["routing_decision"]["model_visible_tools"]) == 1
    assert result["routing_decision"]["execution_attempted"] is False
    assert result["agentweave_provenance_boundary"]["native_record_generated"] is False
    assert all(result["assertions"].values())


def test_agentweave_fixture_preserves_exact_source_descriptor() -> None:
    catalog, _, _ = source_documents()
    _, result = build_fixture()
    selected = result["routing_decision"]["model_visible_tools"][0]
    source = next(tool for tool in catalog if tool["name"] == selected["name"])
    assert selected == source


def test_agentweave_generated_files_are_current() -> None:
    receipt, result = build_fixture()
    expected = {
        FIXTURE / "selection-receipt.json": render(receipt),
        FIXTURE / "fixture-result.json": render(result),
    }
    for path, content in expected.items():
        assert Path(path).read_text(encoding="utf-8") == content
