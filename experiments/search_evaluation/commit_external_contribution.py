#!/usr/bin/env python3
"""Commit one consented external task without publishing its raw content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from asm_protocol.digests import digest_json
from asm_protocol.evaluation_contributions import (
    commit_external_contribution,
    store_private_contribution,
)


def _json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read contribution: {exc}") from exc
    if not isinstance(value, dict):
        raise TypeError("contribution input must be a JSON object")
    return value


def _write_public_task(path: Path, task: dict) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if digest_json(existing) == digest_json(task):
            return
        raise FileExistsError(f"public task already exists with different content: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(task, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a public commitment plus an owner-only local record. No network calls are made."
    )
    parser.add_argument("input", type=Path, help="private contribution JSON; never commit this file")
    parser.add_argument("public_output", type=Path, help="public task commitment JSON")
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--split", choices=["development", "held_out"], required=True)
    parser.add_argument("--received-at", required=True)
    parser.add_argument("--committed-at", required=True)
    parser.add_argument("--judge-profile", default="asm-search-blinded-judge/v0.1-unfrozen")
    args = parser.parse_args()

    committed = commit_external_contribution(
        _json_object(args.input),
        batch_id=args.batch_id,
        split=args.split,
        received_at=args.received_at,
        committed_at=args.committed_at,
        judge_profile=args.judge_profile,
    )
    private_path = store_private_contribution(args.private_dir, committed["private_record"])
    _write_public_task(args.public_output, committed["public_task"])
    print(
        json.dumps(
            {
                "task_id": committed["public_task"]["task_id"],
                "public_output": str(args.public_output),
                "private_record": str(private_path),
                "raw_content_printed": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
