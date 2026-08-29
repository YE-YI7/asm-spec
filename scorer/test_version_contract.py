"""Every runtime-facing version consumes the package single source."""

from __future__ import annotations

from pathlib import Path

from asm_protocol.version import SELECTOR_NAME, __version__
from library_select import SELECTOR_VERSION


def test_selector_version_matches_package_version():
    assert SELECTOR_VERSION == SELECTOR_NAME == f"asm-protocol/{__version__}"


def test_mcp_server_imports_single_version_source():
    source = Path("asm_selector_mcp.py").read_text(encoding="utf-8")
    assert "from library_select import SELECTOR_VERSION" in source
    assert 'version="0.5.1"' not in source
