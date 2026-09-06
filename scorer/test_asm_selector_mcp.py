"""MCP SDK v2 smoke tests for the Python ASM selector server."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import StdioServerParameters
from mcp.client import Client
from mcp.client.stdio import stdio_client


def test_selector_stdio_negotiates_modern_era_and_exposes_tools() -> None:
    async def exercise_server() -> None:
        repo_root = Path(__file__).resolve().parents[1]
        pythonpath = os.pathsep.join(
            [str(repo_root), str(repo_root / "src"), os.environ.get("PYTHONPATH", "")]
        )
        transport = stdio_client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "asm_selector_mcp"],
                cwd=repo_root,
                env={**os.environ, "PYTHONPATH": pythonpath},
            )
        )
        async with Client(transport, mode="2026-07-28") as client:
            assert client.protocol_version == "2026-07-28"
            tools_result = await client.list_tools()
            assert {tool.name for tool in tools_result.tools} == {
                "select_tool",
                "adaptive_select_tool",
                "discover_mcp_servers",
                "validate_application_contract",
                "run_search_replay_tool",
                "plan_search_fallback_tool",
                "list_library_tools",
                "get_tool_manifest",
            }

            result = await client.call_tool(
                "select_tool",
                {
                    "task": "book a refundable flight",
                    "taxonomy": "tool.booking.travel",
                    "required_functions": ["flight_search", "flight_order_create"],
                    "require_approval_for": ["financial_charge"],
                    "fallback_policy": "capability_breadth",
                },
            )
            assert result.is_error is False
            payload = json.loads(result.content[0].text)
            assert payload["approval_required"] is True

    asyncio.run(exercise_server())
