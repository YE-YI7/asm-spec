#!/usr/bin/env python3
"""Tests for the distributable ASM lint command."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from asm_lint import build_report, main, render_markdown


EXAMPLES = ROOT / "examples" / "mcp-server-json"
AS_OF = datetime(2026, 5, 20, tzinfo=timezone.utc)


def test_lints_embedded_manifest_with_reproducible_digest():
    report = build_report(EXAMPLES / "remote-with-asm.server.json", AS_OF)

    assert report["source_kind"] == "mcp_server_json"
    assert report["service_id"] == "example/remote-search@1.0"
    assert report["hash_algorithm"] == "sha256"
    assert report["canonicalization"] == "asm-json-sort-keys-v1"
    assert report["manifest_digest"].startswith("sha256:")
    assert report["statuses"] == {
        "schema": "valid",
        "provenance": "complete",
        "freshness": "fresh",
        "selection_readiness": "not_ready",
    }
    assert "invocation eligibility facts are missing" in report["issues"]


def test_lints_direct_manifest_as_selection_ready(tmp_path):
    source = json.loads((EXAMPLES / "remote-with-asm.server.json").read_text(encoding="utf-8"))
    manifest = source["_meta"]["io.modelcontextprotocol.registry/publisher-provided"]["asm"]
    manifest["invocation"] = {
        "interface": "rest_api",
        "reach": "cloud",
        "agent_operable": True,
    }
    path = tmp_path / "service.asm.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    report = build_report(path, AS_OF)

    assert report["source_kind"] == "asm_manifest"
    assert report["statuses"]["selection_readiness"] == "ready"
    assert report["issues"] == []


def test_missing_asm_fails_default_policy(tmp_path, capsys):
    path = tmp_path / "server.json"
    path.write_text(json.dumps({"name": "io.example/no-asm"}), encoding="utf-8")

    assert main([str(path), "--format", "json", "--as-of", "2026-05-20"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["statuses"]["schema"] == "missing"


def test_markdown_report_is_suitable_for_action_summary():
    report = build_report(EXAMPLES / "remote-with-asm.server.json", AS_OF)
    markdown = render_markdown(report)

    assert "# ASM lint report" in markdown
    assert "asm-json-sort-keys-v1" in markdown
    assert "| Schema | `valid` |" in markdown
    assert report["manifest_digest"] in markdown
