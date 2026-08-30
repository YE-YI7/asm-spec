#!/usr/bin/env python3
"""ASM Selector — an MCP server that lets any MCP client (Claude Desktop, Cursor,
agent hosts) query the ASM tool-value library and pick a tool for a task.

This is ASM's productization wedge: the agent doesn't adopt a schema, it just
calls `select_tool` and gets back which tool to use, why, and the operational
policy (risk / approval / side-effects) to gate the action.

Run (stdio):  python asm_selector_mcp.py     (or `asm-selector` once installed)
Requires:     pip install "asm-protocol[mcp]"
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server import MCPServer

from asm_protocol.adaptive import OwnerContext, adaptive_select
from asm_protocol.federation import MCPRegistryClient
from asm_protocol.preferences import PreferenceLedger, model_from_ledger
from library_select import SELECTOR_VERSION, estimate_monthly_cost, load_library, select

mcp = MCPServer(
    "asm-selector",
    version=SELECTOR_VERSION.removeprefix("asm-protocol/"),
    description="Select agent-operable tools using ASM value and policy metadata.",
)


@mcp.tool()
def select_tool(
    task: str,
    taxonomy: str | None = None,
    agent_reach: str = "cloud",
    user_platform: str = "any",
    required_functions: list[str] | None = None,
    require_approval_for: list[str] | None = None,
    require_agent_completable_setup: bool = False,
    monthly_usage: dict[str, float] | None = None,
    amortization_months: int | None = None,
    fallback_policy: str | None = None,
) -> dict:
    """Pick the best tool from the ASM library for a task.

    Filters out tools the agent can't drive (invocation/reach/platform), tools
    that forbid automation, and tools missing the required functions; then ranks
    the rest cheapest-first. Returns the selected tool plus its operational
    policy so the caller can gate high-stakes actions before invoking.

    Args:
        task: audit/display text; the deterministic core does not interpret it.
        taxonomy: optional ASM taxonomy to scope candidates (e.g. tool.booking.travel).
        agent_reach: 'cloud' (remote/headless) or 'local_device' (runs on user's machine).
        user_platform: e.g. windows, macos, ios, android, web, any.
        required_functions: capability names the tool must have (e.g. ["flight_search"]).
        require_approval_for: side-effects that should force approval (e.g. ["financial_charge","sends_message"]).
        require_agent_completable_setup: if true, drop tools that need a human-in-the-loop
            step (paid signup, OAuth consent, manual approval) the agent cannot complete unattended.
        monthly_usage: expected monthly units keyed by billing dimension.
        amortization_months: period for normalizing a declared one-time purchase.
        fallback_policy: optional 'capability_breadth'; never applied implicitly.
    """
    return select(
        task,
        taxonomy=taxonomy,
        agent_reach=agent_reach,
        user_platform=user_platform,
        required_functions=required_functions or [],
        require_approval_for=require_approval_for or [],
        require_agent_completable_setup=require_agent_completable_setup,
        workload={
            "monthly_units": monthly_usage,
            "amortization_months": amortization_months,
        },
        fallback_policy=fallback_policy,
    )


@mcp.tool()
def adaptive_select_tool(
    task: str,
    taxonomy: str,
    required_functions: list[str] | None = None,
    explicit_service_id: str | None = None,
    installed_service_ids: list[str] | None = None,
    authenticated_service_ids: list[str] | None = None,
    forbidden_service_ids: list[str] | None = None,
    forbidden_side_effects: list[str] | None = None,
    agent_reach: str = "cloud",
    user_platform: str = "any",
    reversible: bool = True,
    max_risk: str = "critical",
    allow_unknown_risk: bool = False,
    interruption_cost: float | None = None,
    monthly_budget: float | None = None,
    budget_currency: str = "USD",
    latency_target_seconds: float | None = None,
    freshness_policy: str = "require_fresh",
    policy: str = "posterior_mean",
) -> dict:
    """EXPERIMENTAL owner-aligned selection with local history, freshness, and VoI.

    Owner history remains in a local JSONL ledger configured by
    ASM_PREFERENCE_LEDGER. The tool returns a model digest and observation
    count, never raw history. Consequential decisions disable exploration.
    """
    ledger_path = Path(
        os.environ.get("ASM_PREFERENCE_LEDGER")
        or Path.home() / ".asm" / "owner-preferences.jsonl"
    )
    model = model_from_ledger(PreferenceLedger(ledger_path))
    return adaptive_select(
        task,
        taxonomy=taxonomy,
        required_functions=required_functions or (),
        agent_reach=agent_reach,
        user_platform=user_platform,
        library=load_library(),
        preference_model=model,
        owner_context=OwnerContext(
            explicit_service_id=explicit_service_id,
            installed_service_ids=tuple(installed_service_ids or ()),
            authenticated_service_ids=tuple(authenticated_service_ids or ()),
            forbidden_service_ids=tuple(forbidden_service_ids or ()),
            forbidden_side_effects=tuple(forbidden_side_effects or ()),
            reversible=reversible,
            max_risk=max_risk,
            allow_unknown_risk=allow_unknown_risk,
            interruption_cost=interruption_cost,
            monthly_budget=monthly_budget,
            budget_currency=budget_currency,
            latency_target_seconds=latency_target_seconds,
        ),
        freshness_policy=freshness_policy,
        policy=policy,
    )


@mcp.tool()
def discover_mcp_servers(
    query: str,
    limit: int = 10,
    max_pages: int = 3,
) -> dict:
    """Search official MCP Registry discovery metadata.

    Returned records are explicitly not selection-ready. An agent must obtain
    and verify current ASM value/policy facts before calling adaptive selection.
    """
    if not 1 <= max_pages <= 10:
        raise ValueError("max_pages must be between 1 and 10 for the MCP tool")
    records = MCPRegistryClient(timeout=5.0).search(query, limit=limit, max_pages=max_pages)
    return {
        "query": query,
        "count": len(records),
        "scan_scope": {
            "bounded": True,
            "max_pages": max_pages,
            "max_registry_records_scanned": max_pages * 100,
        },
        "candidates": [record.to_discovery_candidate() for record in records],
    }


@mcp.tool()
def list_library_tools(taxonomy: str | None = None) -> list[dict]:
    """List tools with invocation facts and honest cost-estimate status."""
    out = []
    for m in load_library():
        if taxonomy and m.get("taxonomy") != taxonomy:
            continue
        inv = m.get("invocation") or {}
        estimate = estimate_monthly_cost(m)
        out.append(
            {
                "service_id": m.get("service_id"),
                "display_name": m.get("display_name"),
                "taxonomy": m.get("taxonomy"),
                "interface": inv.get("interface"),
                "reach": inv.get("reach"),
                "agent_operable": inv.get("agent_operable"),
                "monthly_cost_usd": estimate.monthly_total,
                "cost_estimate": estimate.to_dict(),
            }
        )
    return out


@mcp.tool()
def get_tool_manifest(service_id: str) -> dict:
    """Return the full ASM manifest for a given service_id."""
    for m in load_library():
        if m.get("service_id") == service_id:
            return m
    return {"error": f"no tool with service_id={service_id}"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
