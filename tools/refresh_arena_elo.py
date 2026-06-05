#!/usr/bin/env python3
"""Refresh the LMArena Elo snapshot used by the OpenRouter value router.

Downloads the latest text-leaderboard parquet from the official LMArena
Hugging Face dataset and rebuilds scorer/data/elo_snapshot.json
(overall + coding categories), which ships inside the wheel.

Usage:
    python tools/refresh_arena_elo.py
Requires: pandas, pyarrow  (pip install pandas pyarrow)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "scorer" / "data" / "elo_snapshot.json"
PARQUET_URL = (
    "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/"
    "resolve/main/text/latest-00000-of-00001.parquet"
)
CATEGORIES = ["overall", "coding"]


def main() -> int:
    try:
        import pandas as pd
    except ImportError:
        print("pandas + pyarrow required: pip install pandas pyarrow", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.parent / "_text_latest.parquet"
    print(f"Downloading {PARQUET_URL} ...", file=sys.stderr)
    req = Request(PARQUET_URL, headers={"User-Agent": "asm-arena-refresh/0.1"})
    with urlopen(req, timeout=180) as resp:
        tmp.write_bytes(resp.read())

    df = pd.read_parquet(tmp)
    snap = {
        "source": PARQUET_URL,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "categories": {},
    }
    for cat in CATEGORIES:
        c = df[df["category"] == cat].sort_values("rating", ascending=False)
        if c.empty:
            continue
        models = [
            {
                "model": str(r["model_name"]),
                "org": str(r["organization"]),
                "elo": round(float(r["rating"]), 1),
                "rank": int(r["rank"]),
                "votes": int(r["vote_count"]),
            }
            for _, r in c.iterrows()
        ]
        snap["categories"][cat] = {
            "leaderboard_publish_date": str(c["leaderboard_publish_date"].iloc[0]),
            "elo_min": round(float(c["rating"].min()), 1),
            "elo_max": round(float(c["rating"].max()), 1),
            "n": len(models),
            "models": models,
        }

    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        tmp.unlink()
    except OSError:
        pass
    pub = snap["categories"].get("overall", {}).get("leaderboard_publish_date")
    n = snap["categories"].get("overall", {}).get("n")
    print(f"Wrote {OUT} (publish_date={pub}, overall={n} models)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
