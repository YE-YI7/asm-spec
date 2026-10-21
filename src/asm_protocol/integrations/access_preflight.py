"""Opt-in, declaration-only access preflight for a consumer pilot.

This is not an authorization system. It never reads credentials, fetches a
provider, or invokes tools. The host still owns consent and runtime checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from urllib.parse import urlsplit

from asm_protocol.selection import manifest_digest, select


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamps must have a timezone")
    return result


def access_preflight(
    manifests: Sequence[dict],
    *,
    required_functions: Sequence[str],
    auth_context: str = "anonymous",
    evaluated_at: str | None = None,
    max_age_seconds: int = 86400,
) -> dict:
    """Select among explicit, fresh anonymous-access declarations only.

    A configured credential is deliberately *not* a verified account grant.
    Unknown/stale metadata remains unknown, even when it is schema-valid.
    """
    if auth_context not in {"anonymous", "configured_unverified"}:
        raise ValueError("auth_context must be anonymous or configured_unverified; never supply a credential")
    if isinstance(required_functions, str) or not required_functions or any(
        not isinstance(value, str) or not value for value in required_functions
    ):
        raise ValueError("supply non-empty structured required_functions")
    if type(max_age_seconds) is not int or max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be a positive integer")
    if len(manifests) > 100:
        raise ValueError("pilot supports at most 100 manifests")
    now = _time(evaluated_at) if evaluated_at else datetime.now(timezone.utc)
    considered, eligible, seen = [], [], set()
    for manifest in manifests:
        sid = manifest.get("service_id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError("manifest service IDs must be non-empty and unique")
        seen.add(sid)
        provenance = manifest.get("provenance") or {}
        invocation = manifest.get("invocation") or {}
        status, reason = "unknown", "access_not_declared"
        source = provenance.get("source_url")
        fresh = False
        try:
            url = urlsplit(source)
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.query:
                raise ValueError("public HTTPS source without credentials/query required")
            verified = _time(provenance["last_verified_at"])
            ttl = manifest.get("ttl")
            if type(ttl) is not int or ttl <= 0:
                raise ValueError("explicit positive source TTL required")
            fresh = 0 <= (now - verified).total_seconds() < min(ttl, max_age_seconds)
            if not fresh:
                reason = "source_stale_or_future"
        except (ValueError, TypeError, KeyError, AttributeError):
            source = None
            reason = "source_unusable"
        auth = invocation.get("auth_to_invoke")
        if fresh:
            if auth == "none" and invocation.get("agent_completable_setup") is True:
                status, reason = "anonymous_declared", "provider_declares_anonymous_access"
                eligible.append(manifest)
            elif isinstance(auth, str) and auth and auth not in {"none", "unknown", "unspecified"}:
                status = "requires_authentication" if auth_context == "anonymous" else "needs_account_verification"
                reason = "no_credential_configured" if auth_context == "anonymous" else "credential_presence_is_not_an_access_grant"
            elif auth == "none" and invocation.get("agent_completable_setup") is False:
                status, reason = "setup_required", "provider_declares_a_human_setup_step"
        considered.append({
            "service_id": sid, "status": status, "reason": reason,
            "basis": "provider_documentation", "source_url": source,
            "last_verified_at": provenance.get("last_verified_at"),
            "manifest_digest": manifest_digest(manifest),
            "runtime_access_verified": False,
        })
    decision = select(
        "consumer-supplied structured function requirement",
        required_functions=required_functions,
        library=eligible,
    )
    return {
        "receipt_type": "access_preflight_pilot", "receipt_version": "0.1",
        "evaluated_at": now.isoformat(), "auth_context": auth_context,
        "required_functions": list(required_functions),
        "considered": considered, "decision": decision,
        "execution_authorized": False, "additional_model_calls": 0,
        "limits": "Documentation-based path hint only; host authorization, current quotas, price and runtime success remain unverified.",
    }
