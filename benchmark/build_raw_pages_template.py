#!/usr/bin/env python3
"""Build a human-review checklist for ToolSelect-Bench raw-page evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmark.raw_pages import build_review_template  # noqa: E402
from library_select import load_library  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=ROOT / "benchmark/tasks.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tasks = [
        json.loads(line) for line in args.tasks.read_text(encoding="utf-8").splitlines()
    ]
    template = build_review_template(tasks, load_library())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"wrote review checklist for {len(template['services'])} services to "
        f"{args.output}"
    )
    print("pages are empty by design; a reviewer must map official text to fact paths")


if __name__ == "__main__":
    main()
