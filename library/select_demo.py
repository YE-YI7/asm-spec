#!/usr/bin/env python3
"""Demo: an agent selecting a TOOL (not a model) from the ASM library.

Implements the confirmed priority order:
  gate 1: agent can invoke it      (agent_operable AND reach matches agent env)
  gate 2: agent is allowed         (usage_terms.automation_allowed != 'no';
                                     auth the user can satisfy -> assumed green-lit)
  gate 3: meets task requirements   (required functions present; platform compatible)
  score:  among survivors, rank by cost (free first), then feature richness

Run: python library/select_demo.py
"""
from __future__ import annotations
import json, glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENTRIES = [json.loads(Path(p).read_text(encoding="utf-8"))
           for p in glob.glob(str(HERE / "**" / "*.asm.json"), recursive=True)]


def monthly_cost(m):
    dims = (m.get("pricing") or {}).get("billing_dimensions") or []
    free = "free_tier" in (m.get("payment") or {}).get("methods", [])
    base = 0.0 if free else 1e9
    saw_zero_price = False
    for d in dims:
        c, u = d.get("cost_per_unit", 0), d.get("unit", "")
        if c == 0:
            saw_zero_price = True
            continue
        base = min(base, c if "month" in u else c/12 if "year" in u else c/24)  # one-time amortized ~24mo
    if base == 1e9 and saw_zero_price:
        return 0.0
    return 0.0 if free else base


def select(task, *, agent_reach, user_platform, required_functions, taxonomy=None):
    kept, rejected = [], []
    pool = [m for m in ENTRIES if taxonomy is None or m.get("taxonomy") == taxonomy]
    for m in pool:
        inv = m.get("invocation", {})
        name = m["display_name"]
        # gate 1: invocable by THIS agent
        if not inv.get("agent_operable"):
            rejected.append((name, "not agent-operable")); continue
        if inv.get("reach") == "local_device" and agent_reach != "local_device":
            rejected.append((name, f"reach=local_device but agent is {agent_reach} (can't drive remotely)")); continue
        # gate 2: allowed
        if (m.get("usage_terms") or {}).get("automation_allowed") == "no":
            rejected.append((name, "ToS forbids automation")); continue
        # gate 3: platform + task fit
        plats = inv.get("platforms", [])
        # 'web' (browser) and 'any' satisfy every platform; otherwise need an explicit match
        if not ({"any", "web"} & set(plats)) and user_platform not in plats:
            rejected.append((name, f"platform {user_platform} unsupported ({plats})")); continue
        funcs = set((m.get("capabilities") or {}).get("functions", []))
        missing = [f for f in required_functions if f not in funcs]
        if missing:
            rejected.append((name, f"missing required: {missing}")); continue
        kept.append(m)
    kept.sort(key=lambda m: (monthly_cost(m), -len((m.get("capabilities") or {}).get("functions", []))))
    return kept, rejected


def show(title, task, **ctx):
    print(f"\n=== {title} ===")
    print(f"task: {task}\nagent env: reach={ctx['agent_reach']}, user_platform={ctx['user_platform']}, "
          f"requires={ctx['required_functions']}")
    kept, rejected = select(task, **ctx)
    print("\n  PICK ->", kept[0]["display_name"] if kept else "(none eligible)",
          f"(${monthly_cost(kept[0]):.2f}/mo)" if kept else "")
    if kept:
        ops = kept[0].get("operational_constraints") or {}
        approval = ops.get("approval") or {}
        if ops:
            print("  policy:",
                  f"risk={ops.get('risk_class', 'unknown')},",
                  f"approval={approval.get('required', 'unknown')},",
                  f"side_effects={ops.get('side_effects', [])}")
    for m in kept[1:]:
        print(f"   alt:  {m['display_name']} (${monthly_cost(m):.2f}/mo)")
    print("  filtered out:")
    for n, why in rejected:
        print(f"   - {n}: {why}")


if __name__ == "__main__":
    show("Cloud agent, Windows user: store study plan + daily reminders",
         "make a study plan and remind me daily",
         taxonomy="tool.productivity.task_management",
         agent_reach="cloud", user_platform="windows",
         required_functions=["reminders", "recurring_tasks"])

    show("Same, but user also wants a built-in pomodoro timer",
         "study plan + daily reminders + pomodoro",
         taxonomy="tool.productivity.task_management",
         agent_reach="cloud", user_platform="windows",
         required_functions=["reminders", "recurring_tasks", "pomodoro_timer"])

    show("Cloud agent, Windows user: edit an image / make a poster",
         "edit this image and lay out a poster",
         taxonomy="tool.creative.design",
         agent_reach="cloud", user_platform="windows",
         required_functions=["photo_editing"])

    show("Research agent: collect academic sources with citation metadata",
         "find papers and export citation metadata",
         taxonomy="tool.research.academic",
         agent_reach="cloud", user_platform="windows",
         required_functions=["paper_search", "metadata_export"])

    show("Assistant agent: send a user-visible team update",
         "send a project update to the team",
         taxonomy="tool.communication.chat",
         agent_reach="cloud", user_platform="windows",
         required_functions=["chat_send"])

    show("Coding agent: open an issue and prepare a PR",
         "create an issue and prepare a pull request",
         taxonomy="tool.development.repository",
         agent_reach="cloud", user_platform="windows",
         required_functions=["issue_create", "pull_request_create"])

    show("Travel agent: search and book a flight",
         "find and book a refundable flight",
         taxonomy="tool.booking.travel",
         agent_reach="cloud", user_platform="windows",
         required_functions=["flight_search", "flight_order_create"])
