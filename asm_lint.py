#!/usr/bin/env python3
"""Lint an ASM manifest or MCP server.json and emit a reproducible report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from library_select import ASM_JSON_CANONICALIZATION, HASH_ALGORITHM, manifest_digest
from mcp_server_json_asm import extract_asm, load_json, validate_manifest

PROVENANCE_FIELDS = ("source_url", "retrieved_at", "last_verified_at", "verification_status")
VALUE_FIELDS = ("pricing", "quality", "sla")
FRESH_DAYS = 30
STALE_DAYS = 90


def parse_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def parse_as_of(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if len(value) == 10:
        value += "T23:59:59Z"
    return parse_datetime(value)


def freshness_status(last_verified_at: str | None, as_of: datetime) -> tuple[str, int | None]:
    if not last_verified_at:
        return "unknown", None
    try:
        verified = parse_datetime(last_verified_at)
    except (TypeError, ValueError):
        return "invalid", None
    age_days = max(0, (as_of - verified).days)
    if age_days <= FRESH_DAYS:
        return "fresh", age_days
    if age_days <= STALE_DAYS:
        return "stale", age_days
    return "expired", age_days


def build_report(path: str | Path, as_of: datetime) -> dict[str, Any]:
    path = Path(path)
    try:
        document = load_json(path)
    except Exception as exc:
        return {
            "report_version": "1",
            "path": str(path),
            "source_kind": "unknown",
            "statuses": {
                "schema": "invalid",
                "provenance": "missing",
                "freshness": "unknown",
                "selection_readiness": "not_ready",
            },
            "issues": [str(exc)],
        }

    extraction_warnings: list[str] = []
    extraction_errors: list[str] = []
    if "asm_version" in document:
        source_kind = "asm_manifest"
        manifest = document
    else:
        source_kind = "mcp_server_json"
        manifest, extraction_warnings, extraction_errors = extract_asm(document)

    if manifest is None:
        return {
            "report_version": "1",
            "path": str(path),
            "source_kind": source_kind,
            "statuses": {
                "schema": "missing",
                "provenance": "missing",
                "freshness": "unknown",
                "selection_readiness": "not_ready",
            },
            "issues": extraction_errors + extraction_warnings,
        }

    schema_errors = validate_manifest(manifest)
    provenance = manifest.get("provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    missing_provenance = [field for field in PROVENANCE_FIELDS if not provenance.get(field)]
    provenance_status = "complete" if not missing_provenance else "incomplete"
    freshness, age_days = freshness_status(provenance.get("last_verified_at"), as_of)

    readiness_issues: list[str] = []
    if schema_errors:
        readiness_issues.append("manifest does not pass the ASM schema")
    if missing_provenance:
        readiness_issues.append("provenance is incomplete")
    if not isinstance(manifest.get("invocation"), dict):
        readiness_issues.append("invocation eligibility facts are missing")
    if not any(field in manifest for field in VALUE_FIELDS):
        readiness_issues.append("no pricing, quality, or SLA selection facts are present")

    issues = extraction_errors + schema_errors
    issues += [f"missing provenance.{field}" for field in missing_provenance]
    issues += readiness_issues
    return {
        "report_version": "1",
        "path": str(path),
        "source_kind": source_kind,
        "service_id": manifest.get("service_id"),
        "hash_algorithm": HASH_ALGORITHM,
        "canonicalization": ASM_JSON_CANONICALIZATION,
        "manifest_digest": manifest_digest(manifest),
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "statuses": {
            "schema": "valid" if not schema_errors else "invalid",
            "provenance": provenance_status,
            "freshness": freshness,
            "selection_readiness": "ready" if not readiness_issues else "not_ready",
        },
        "verification_age_days": age_days,
        "issues": issues,
        "warnings": extraction_warnings,
    }


def render_human(report: dict[str, Any]) -> str:
    statuses = report["statuses"]
    lines = [
        f"ASM lint: {report['path']}",
        f"Service: {report.get('service_id') or 'unknown'}",
        f"Hash algorithm: {report.get('hash_algorithm') or 'unavailable'}",
        f"Canonicalization: {report.get('canonicalization') or 'unavailable'}",
        f"Digest: {report.get('manifest_digest') or 'unavailable'}",
        f"Schema: {statuses['schema']}",
        f"Provenance: {statuses['provenance']}",
        f"Freshness: {statuses['freshness']}",
        f"Selection readiness: {statuses['selection_readiness']}",
    ]
    for issue in report.get("issues", []):
        lines.append(f"Issue: {issue}")
    for warning in report.get("warnings", []):
        lines.append(f"Warning: {warning}")
    return "\n".join(lines) + "\n"


def render_markdown(report: dict[str, Any]) -> str:
    statuses = report["statuses"]
    lines = [
        "# ASM lint report",
        "",
        f"- **File:** `{report['path']}`",
        f"- **Service:** `{report.get('service_id') or 'unknown'}`",
        f"- **Hash algorithm:** `{report.get('hash_algorithm') or 'unavailable'}`",
        f"- **Canonicalization:** `{report.get('canonicalization') or 'unavailable'}`",
        f"- **Manifest digest:** `{report.get('manifest_digest') or 'unavailable'}`",
        "",
        "| Check | Status |",
        "|---|---|",
        f"| Schema | `{statuses['schema']}` |",
        f"| Provenance | `{statuses['provenance']}` |",
        f"| Freshness | `{statuses['freshness']}` |",
        f"| Selection readiness | `{statuses['selection_readiness']}` |",
    ]
    findings = report.get("issues", []) + report.get("warnings", [])
    if findings:
        lines += ["", "## Findings", ""] + [f"- {finding}" for finding in findings]
    return "\n".join(lines) + "\n"


def should_fail(report: dict[str, Any], fail_on: str) -> bool:
    statuses = report["statuses"]
    if statuses["schema"] != "valid":
        return True
    if fail_on == "invalid":
        return False
    if fail_on == "not-ready":
        return statuses["selection_readiness"] != "ready"
    if fail_on == "expired":
        return statuses["freshness"] in {"expired", "unknown", "invalid"}
    if fail_on == "stale":
        return statuses["freshness"] != "fresh"
    raise ValueError(f"unknown fail-on policy: {fail_on}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to an ASM manifest or MCP Registry server.json")
    parser.add_argument("--format", choices=("human", "json", "markdown"), default="human")
    parser.add_argument("--output", type=Path, help="write the report to this path")
    parser.add_argument("--as-of", help="ISO date/datetime for deterministic freshness checks")
    parser.add_argument(
        "--fail-on",
        choices=("invalid", "not-ready", "expired", "stale"),
        default="invalid",
        help="CI failure threshold (default: invalid)",
    )
    args = parser.parse_args(argv)
    try:
        report = build_report(args.input, parse_as_of(args.as_of))
    except ValueError as exc:
        parser.error(str(exc))

    if args.format == "json":
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    elif args.format == "markdown":
        rendered = render_markdown(report)
    else:
        rendered = render_human(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(rendered)
    return 1 if should_fail(report, args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
