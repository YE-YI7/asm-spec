#!/usr/bin/env python3
"""Demo: an agent selecting a TOOL (not a model) from the ASM library.

Thin wrapper over the shared selector in library_select.py (repo root), so the
demo, the CLI, and the MCP server all run the exact same selection logic.

Run: python library/select_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root for library_select
from library_select import estimate_monthly_cost, policy_of, rank  # noqa: E402


def cost_label(manifest):
    estimate = estimate_monthly_cost(manifest)
    if estimate.monthly_total is not None:
        return f"${estimate.monthly_total:.2f}/mo"
    return f"{estimate.status} cost"


def show(title, task, **ctx):
    print(f"\n=== {title} ===")
    print(f"task: {task}\nagent env: reach={ctx['agent_reach']}, "
          f"user_platform={ctx['user_platform']}, requires={ctx['required_functions']}")
    kept, rejected = rank(task, **ctx)
    if kept:
        top = kept[0]
        pol = policy_of(top)
        print(f"\n  PICK -> {top['display_name']} ({cost_label(top)})")
        if top.get("operational_constraints"):
            print("  policy:",
                  f"risk={pol['risk_class']},",
                  f"approval={pol['approval_policy']},",
                  f"side_effects={pol['side_effects']}")
        inv = top.get("invocation") or {}
        if inv.get("agent_completable_setup") is not None:
            print(f"  setup: agent_completable={inv.get('agent_completable_setup')},",
                  f"requires={inv.get('setup_requires', [])}")
        for m in kept[1:]:
            print(f"   alt:  {m['display_name']} ({cost_label(m)})")
    else:
        print("\n  PICK -> (none eligible)")
    print("  filtered out:")
    for r in rejected:
        print(f"   - {r['service']}: {r['reason']}")


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

    show("Autonomous agent (no human available for setup): pull real-estate data",
         "get property and market data for an address",
         taxonomy="tool.data.real_estate",
         agent_reach="cloud", user_platform="windows",
         required_functions=["real_estate_data"],
         require_agent_completable_setup=True)
