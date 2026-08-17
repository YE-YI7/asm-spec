#!/usr/bin/env python3
"""Extract and validate ASM metadata embedded in MCP Registry server.json files."""

from __future__ import annotations

import argparse
import importlib.resources
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - exercised only without optional dependency
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema" / "asm-v0.3.schema.json"
PUBLISHER_META_KEY = "io.modelcontextprotocol.registry/publisher-provided"
RECOMMENDED_VALUE_FIELDS = ("pricing", "sla", "quality", "provenance", "payment")


@dataclass
class InspectionResult:
    path: str
    has_asm: bool
    valid_asm: bool
    can_convert: bool
    asm_service_id: str | None = None
    asm_taxonomy: str | None = None
    missing_recommended_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    asm_manifest: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        data = {
            "path": self.path,
            "has_asm": self.has_asm,
            "valid_asm": self.valid_asm,
            "can_convert": self.can_convert,
            "asm_service_id": self.asm_service_id,
            "asm_taxonomy": self.asm_taxonomy,
            "missing_recommended_fields": self.missing_recommended_fields,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        if self.asm_manifest is not None:
            data["asm_manifest"] = self.asm_manifest
        return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError("server.json root must be an object")
    return data


def extract_asm(server_json: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    meta = server_json.get("_meta")
    if not isinstance(meta, dict):
        return None, ["No _meta object found; this server.json has no inline ASM metadata."], errors

    publisher = meta.get(PUBLISHER_META_KEY)
    if not isinstance(publisher, dict):
        return None, [f"No _meta.{PUBLISHER_META_KEY} object found; no publisher-provided ASM metadata."], errors

    asm = publisher.get("asm")
    asm_url = publisher.get("asm_url")
    if asm is None and asm_url:
        return None, [f"ASM is referenced by asm_url={asm_url!r}; inline conversion is unavailable."], errors
    if asm is None:
        return None, ["No publisher-provided asm object found."], errors
    if not isinstance(asm, dict):
        return None, warnings, ["publisher-provided asm must be a JSON object."]
    return asm, warnings, errors


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    if Draft202012Validator is None:
        required = {"asm_version", "service_id", "taxonomy"}
        return [f"Missing required field: {field}" for field in sorted(required - set(manifest))]

    if SCHEMA_PATH.exists():
        schema = load_json(SCHEMA_PATH)
    else:
        resource = importlib.resources.files("asm_schema").joinpath("asm-v0.3.schema.json")
        schema = json.loads(resource.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{path}: {err.message}")
    return errors


def inspect_server_json(path: str | Path) -> InspectionResult:
    path = Path(path)
    try:
        server_json = load_json(path)
    except Exception as exc:
        return InspectionResult(path=str(path), has_asm=False, valid_asm=False, can_convert=False, errors=[str(exc)])

    asm, warnings, extraction_errors = extract_asm(server_json)
    if asm is None:
        return InspectionResult(
            path=str(path),
            has_asm=False,
            valid_asm=False,
            can_convert=False,
            warnings=warnings,
            errors=extraction_errors,
        )

    validation_errors = validate_manifest(asm)
    missing = [field for field in RECOMMENDED_VALUE_FIELDS if field not in asm]
    return InspectionResult(
        path=str(path),
        has_asm=True,
        valid_asm=not validation_errors,
        can_convert=not validation_errors,
        asm_service_id=asm.get("service_id"),
        asm_taxonomy=asm.get("taxonomy"),
        missing_recommended_fields=missing,
        warnings=warnings,
        errors=extraction_errors + validation_errors,
        asm_manifest=asm,
    )


def print_human(result: InspectionResult) -> None:
    print(f"File: {result.path}")
    if not result.has_asm:
        print("ASM metadata: missing")
    else:
        print("ASM metadata: found")
        print(f"Service: {result.asm_service_id or 'unknown'}")
        print(f"Taxonomy: {result.asm_taxonomy or 'unknown'}")
        print(f"Schema validation: {'pass' if result.valid_asm else 'fail'}")
        if result.missing_recommended_fields:
            print("Missing recommended value fields: " + ", ".join(result.missing_recommended_fields))
        else:
            print("Recommended value fields: complete")

    for warning in result.warnings:
        print(f"Warning: {warning}")
    for error in result.errors:
        print(f"Error: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ASM metadata embedded in MCP Registry server.json files")
    parser.add_argument("server_json", help="Path to server.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable inspection JSON")
    parser.add_argument("--write-out", help="Write extracted ASM manifest to this .asm.json path")
    args = parser.parse_args(argv)

    result = inspect_server_json(args.server_json)
    if args.write_out and result.asm_manifest and result.valid_asm:
        out = Path(args.write_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.asm_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    else:
        print_human(result)

    if result.errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
