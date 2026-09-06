"""Named RFC 8785 JSON commitments for ASM draft application contracts."""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785

DIGEST_PROFILE = "rfc8785+jcs-sha256-v0.1"


def canonical_json(value: Any) -> bytes:
    """Return RFC 8785 canonical UTF-8 bytes, rejecting non-I-JSON values."""
    return rfc8785.dumps(value)


def digest_json(value: Any) -> str:
    """Return a profile-compatible SHA-256 digest of canonical JSON."""
    return f"sha256:{hashlib.sha256(canonical_json(value)).hexdigest()}"


def digest_query(query: str) -> str:
    """Commit to a private query without publishing the query itself."""
    return digest_json({"query": query})


__all__ = ["DIGEST_PROFILE", "canonical_json", "digest_json", "digest_query"]
