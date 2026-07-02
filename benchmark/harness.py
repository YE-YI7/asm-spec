#!/usr/bin/env python3
"""ToolSelect-Bench harness: run subjects over tasks.jsonl, score, report.

Conditions
  names_only  the subject sees candidate names + one-line descriptions only —
              approximating an agent choosing tools today, without machine-
              readable value metadata.
  asm         the subject sees the candidates' ASM manifests (trimmed).

Metrics (pre-registered; see README.md)
  correct      pick is in the ground-truth correct set
  violation    pick appears in violations_if (a nameable constraint breach)
  overspend    picked monthly cost minus min eligible cost (cost-typed tasks)

Subjects
  random       uniform pick over candidates (seeded) — floor reference
  llm:<model>  any OpenRouter chat model; needs OPENROUTER_API_KEY.
               The LLM receives ONLY the task prompt + condition materials.

Honesty rules: our own ranker (library_select) is NOT a benchmark subject or
oracle — ground truth is logic-derived at generation time. All raw picks are
saved so scoring is independently re-checkable.

Usage
  python benchmark/harness.py --subject random
  python benchmark/harness.py --subject llm:openai/gpt-4o-mini --condition names_only
  python benchmark/harness.py --subject llm:anthropic/claude-sonnet-4.6 --limit 10
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONDITIONS = ("names_only", "asm")


def load_tasks(limit: int | None = None) -> list[dict]:
    tasks = [json.loads(l) for l in (HERE / "tasks.jsonl").open(encoding="utf-8")]
    return tasks[:limit] if limit else tasks


# ---------------------------------------------------------------- subjects --
def subject_random(task: dict, condition: str, seed: int = 7) -> str:
    rng = random.Random(f"{seed}:{task['task_id']}")
    return rng.choice(task["candidates"])


def _openrouter_chat(model: str, prompt: str, retries: int = 3) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY not set — needed for llm:* subjects")
    body = json.dumps({"model": model, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _materials(task: dict, condition: str) -> str:
    if condition == "names_only":
        lines = [f"- {c['service_id']}: {c['name']} — {c['description'] or '(no description)'}"
                 for c in task["conditions"]["names_only"]]
        return "Candidate tools:\n" + "\n".join(lines)
    return ("Candidate tools (ASM manifests):\n"
            + json.dumps(task["conditions"]["asm"], ensure_ascii=False))


def _parse_pick(text: str, candidates: list[str]) -> str | None:
    for sid in sorted(candidates, key=len, reverse=True):
        if sid in text:
            return sid
    # bare name fallback: match the org/tool stem
    for sid in candidates:
        stem = re.split(r"[/@]", sid)[1] if "/" in sid else sid
        if stem and stem.lower() in text.lower():
            return sid
    return None


def subject_llm(model: str, task: dict, condition: str) -> str | None:
    prompt = (f"{task['prompt']}\n\n{_materials(task, condition)}\n\n"
              "Reply with exactly one service_id and nothing else.")
    return _parse_pick(_openrouter_chat(model, prompt), task["candidates"])


# ----------------------------------------------------------------- scoring --
def score(tasks: list[dict], picks: dict[str, str | None]) -> dict:
    n = len(tasks)
    correct = violations = unparsed = 0
    overspends: list[float] = []
    for t in tasks:
        pick = picks.get(t["task_id"])
        gt = t["ground_truth"]
        if pick is None:
            unparsed += 1
            continue
        if pick in gt["correct"]:
            correct += 1
        if pick in gt["violations_if"]:
            violations += 1
        costs = gt.get("eligible_costs_usd_month")
        if costs and pick in costs:
            overspends.append(costs[pick] - min(costs.values()))
    return {
        "n": n,
        "correct_rate": round(correct / n, 3),
        "violation_rate": round(violations / n, 3),
        "unparsed": unparsed,
        "mean_overspend_usd_month": (round(sum(overspends) / len(overspends), 2)
                                     if overspends else None),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True,
                    help="'random' or 'llm:<openrouter-model-id>'")
    ap.add_argument("--condition", choices=CONDITIONS, default=None,
                    help="default: run both")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    tasks = load_tasks(args.limit)
    conditions = [args.condition] if args.condition else list(CONDITIONS)
    results_dir = HERE / "results"
    results_dir.mkdir(exist_ok=True)

    for cond in conditions:
        picks: dict[str, str | None] = {}
        for t in tasks:
            if args.subject == "random":
                picks[t["task_id"]] = subject_random(t, cond)
            elif args.subject.startswith("llm:"):
                picks[t["task_id"]] = subject_llm(args.subject[4:], t, cond)
            else:
                raise SystemExit(f"unknown subject: {args.subject}")
        s = score(tasks, picks)
        tag = re.sub(r"[^A-Za-z0-9_.-]", "_", args.subject)
        out = results_dir / f"{tag}__{cond}.json"
        out.write_text(json.dumps(
            {"subject": args.subject, "condition": cond, "metrics": s,
             "picks": picks}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{args.subject:40} {cond:11} correct={s['correct_rate']:.0%} "
              f"violations={s['violation_rate']:.0%} "
              f"overspend=${s['mean_overspend_usd_month']}/mo "
              f"unparsed={s['unparsed']}  -> {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
