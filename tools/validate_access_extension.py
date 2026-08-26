#!/usr/bin/env python3
"""Validate one candidate AI Catalog access-extension value."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "asm-ai-catalog-access-v0.1.schema.json"


def validation_errors(document: dict) -> list[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    args = parser.parse_args(argv)
    document = json.loads(args.document.read_text(encoding="utf-8"))
    errors = validation_errors(document)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"PASS: {args.document}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
