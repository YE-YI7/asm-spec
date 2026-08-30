"""Federated discovery adapters.

Discovery records identify possible tools. They are deliberately not promoted
to selection-ready ASM manifests until value, policy, and freshness facts have
been obtained from an authoritative source.
"""

from .mcp_registry import MCPRegistryClient, MCPRegistryRecord, RegistryPage

__all__ = ["MCPRegistryClient", "MCPRegistryRecord", "RegistryPage"]
