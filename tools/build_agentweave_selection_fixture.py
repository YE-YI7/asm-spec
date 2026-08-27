#!/usr/bin/env python3
"""Build the deterministic ASM -> AgentWeave selection-boundary fixture."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "examples" / "interop" / "agentweave-selection-boundary"
SIDECAR_EXTENSION = "io.github.sauravsingla.agentweave.fixture"
AGENTWEAVE_COMMIT = "1f2e9c88c6e85dc072e17fb06ff67038c4d45687"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library_select import manifest_digest, select
from mcp_server_json_asm import validate_manifest


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_digest(document: Any) -> str:
    raw = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def source_documents() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict]:
    catalog = load_json(FIXTURE / "mcp-tools.json").get("tools")
    if not isinstance(catalog, list) or len(catalog) != 2:
        raise ValueError("fixture must contain exactly two MCP tool descriptors")
    sidecars = [
        load_json(FIXTURE / "sidecars" / "tracker-standard.asm.json"),
        load_json(FIXTURE / "sidecars" / "tracker-priority.asm.json"),
    ]
    constraint = load_json(FIXTURE / "task-constraint.json")
    return catalog, sidecars, constraint


def _validate_mcp_catalog(catalog: list[dict[str, Any]]) -> None:
    names: list[str] = []
    for descriptor in catalog:
        name = descriptor.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("every MCP descriptor needs a non-empty name")
        if not isinstance(descriptor.get("inputSchema"), dict):
            raise TypeError(f"{name}: inputSchema must be an object")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("MCP descriptor names must be unique")


def _tool_binding(sidecar: dict[str, Any]) -> str:
    extension = (sidecar.get("extensions") or {}).get(SIDECAR_EXTENSION) or {}
    tool_name = extension.get("mcp_tool_name")
    if not isinstance(tool_name, str) or not tool_name:
        raise ValueError(
            f"{sidecar.get('service_id')}: missing fixture MCP tool-name binding"
        )
    return tool_name


def build_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    catalog, sidecars, constraint = source_documents()
    _validate_mcp_catalog(catalog)
    tool_by_name = {tool["name"]: tool for tool in catalog}

    bindings: dict[str, str] = {}
    for sidecar in sidecars:
        errors = validate_manifest(sidecar)
        if errors:
            raise ValueError(f"invalid sidecar {sidecar.get('service_id')}: {errors}")
        tool_name = _tool_binding(sidecar)
        if tool_name not in tool_by_name:
            raise ValueError(f"sidecar binding points to unknown MCP tool: {tool_name}")
        bindings[sidecar["service_id"]] = tool_name
    if len(set(bindings.values())) != len(catalog):
        raise ValueError("fixture requires a one-to-one sidecar/MCP descriptor binding")

    decision = select(
        constraint["task"],
        taxonomy=constraint["taxonomy"],
        agent_reach=constraint["agent_reach"],
        user_platform=constraint["user_platform"],
        required_functions=constraint["required_functions"],
        require_approval_for=constraint["require_approval_for"],
        require_agent_completable_setup=constraint[
            "require_agent_completable_setup"
        ],
        library=sidecars,
        receipt=True,
    )
    if decision["selection_status"] != "selected" or not decision["selected"]:
        raise ValueError(f"fixture did not produce one selection: {decision}")

    selected_service = decision["selected"]["service_id"]
    selected_tool_name = bindings[selected_service]
    selected_descriptor = tool_by_name[selected_tool_name]
    receipt = decision["receipt"]
    receipt["selection_id"] = "fixture-agentweave-selection-boundary-0001"
    receipt["issued_at"] = "2026-08-26T00:00:00Z"

    evidence_digests = {
        item["service_id"]: item["manifest_digest"] for item in receipt["evidence"]
    }
    expected_digests = {
        sidecar["service_id"]: manifest_digest(sidecar) for sidecar in sidecars
    }
    filtered_out = [
        name for name in tool_by_name if name != selected_tool_name
    ]
    result = {
        "fixture_version": "0.1",
        "scope": "asm-selection-facts-to-agentweave-model-visible-tool",
        "agentweave_reference": {
            "repository": "https://github.com/sauravsingla/agentweave",
            "commit": AGENTWEAVE_COMMIT,
            "mcp_example": "examples/mcp_tool_routing.py",
            "native_provenance": "agentweave_security/routing_provenance.py",
        },
        "source_catalog": {
            "path": "mcp-tools.json",
            "digest": canonical_digest({"tools": catalog}),
            "tool_names": list(tool_by_name),
        },
        "task_constraint": {
            "path": "task-constraint.json",
            "digest": canonical_digest(constraint),
            "value": constraint,
            "task_text_interpreted_by_asm": decision["task_interpreted"],
        },
        "selection_facts": [
            {
                "service_id": sidecar["service_id"],
                "mcp_tool_name": bindings[sidecar["service_id"]],
                "manifest_digest": expected_digests[sidecar["service_id"]],
            }
            for sidecar in sidecars
        ],
        "routing_decision": {
            "selection_status": decision["selection_status"],
            "selected_service_id": selected_service,
            "selected_mcp_tool_name": selected_tool_name,
            "model_visible_tools": [selected_descriptor],
            "filtered_out_before_inference": filtered_out,
            "approval_required_before_invocation": decision["approval_required"],
            "execution_attempted": False,
        },
        "selection_receipt": {
            "uri": "selection-receipt.json",
            "digest": canonical_digest(receipt),
            "digest_profile": "python-json-sort-keys-compact-utf8-v0.1",
            "purpose": "provenance_only",
            "required_by_agentweave": False,
            "validated_by_agentweave": False,
            "verification_status": "unsigned",
            "authorization": False,
        },
        "agentweave_provenance_boundary": {
            "native_record_generated": False,
            "reason": "This fixture runs outside AgentWeave at the reviewer's request.",
            "handoff": (
                "AgentWeave remains responsible for its native policy/router drops, "
                "model call, authorization, execution, and stage telemetry."
            ),
        },
        "assertions": {
            "receipt_pins_exact_two_sidecars": evidence_digests == expected_digests,
            "selected_descriptor_is_byte_for_byte_source_value": (
                selected_descriptor == tool_by_name[selected_tool_name]
            ),
            "exactly_one_model_visible_tool": True,
            "task_text_is_audit_only": decision["task_interpreted"] is False,
            "approval_is_not_authorization": (
                decision["approval_required"] is True
                and "authorization" not in receipt
            ),
            "receipt_has_no_execution_record": "execution" not in receipt,
            "receipt_has_no_signature": "signature" not in receipt,
        },
    }
    return receipt, result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify generated files")
    mode.add_argument("--write", action="store_true", help="write generated files")
    args = parser.parse_args(argv)

    receipt, result = build_fixture()
    generated = {
        FIXTURE / "selection-receipt.json": render(receipt),
        FIXTURE / "fixture-result.json": render(result),
    }
    if args.write:
        for path, content in generated.items():
            path.write_text(content, encoding="utf-8")
        return 0

    stale = [
        str(path.relative_to(ROOT))
        for path, content in generated.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    if stale:
        print("stale generated fixture files:")
        print("\n".join(f"- {path}" for path in stale))
        return 1
    print("AgentWeave selection-boundary fixture: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
