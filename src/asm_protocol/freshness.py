"""Selection-time freshness and invocation-surface identity gates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Mapping


FreshnessStatus = Literal["fresh", "stale", "expired", "unknown", "invalid"]
FreshnessPolicy = Literal["require_fresh", "allow_stale", "allow_unknown"]
CLAIM_EVIDENCE_EXTENSION = "io.github.ye-yi7.asm.claim-evidence"


def _utc(value: datetime | None = None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        raise ValueError("freshness clock must include a timezone")
    return result.astimezone(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class FreshnessAssessment:
    status: FreshnessStatus
    reference_timestamp: str | None
    age_seconds: int | None
    source: str | None
    verification_status: str | None
    cache_expired: bool | None
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def assess_manifest_freshness(
    manifest: Mapping,
    *,
    now: datetime | None = None,
    fresh_for: timedelta = timedelta(days=30),
    stale_for: timedelta = timedelta(days=90),
    fetched_at: datetime | None = None,
) -> FreshnessAssessment:
    """Assess verification age separately from HTTP/cache TTL.

    `provenance.last_verified_at` is evidence age. `ttl` only controls whether a
    fetched representation may be reused and never makes an old claim fresh.
    """
    current = _utc(now)
    provenance = manifest.get("provenance") or {}
    raw = provenance.get("last_verified_at")
    verification_status = provenance.get("verification_status")
    source = provenance.get("source_url")
    cache_expired = None
    ttl = manifest.get("ttl")
    if fetched_at is not None and isinstance(ttl, int) and ttl >= 0:
        cache_expired = current >= _utc(fetched_at) + timedelta(seconds=ttl)
    if not raw:
        return FreshnessAssessment(
            "unknown", None, None, source, verification_status, cache_expired,
            "provenance.last_verified_at is missing",
        )
    try:
        verified = parse_timestamp(str(raw))
    except (TypeError, ValueError) as exc:
        return FreshnessAssessment(
            "invalid", str(raw), None, source, verification_status, cache_expired,
            f"invalid provenance.last_verified_at: {exc}",
        )
    age = max(current - verified, timedelta(0))
    if age <= fresh_for:
        status: FreshnessStatus = "fresh"
    elif age <= stale_for:
        status = "stale"
    else:
        status = "expired"
    return FreshnessAssessment(
        status,
        verified.strftime("%Y-%m-%dT%H:%M:%SZ"),
        int(age.total_seconds()),
        source,
        verification_status,
        cache_expired,
        f"manifest verification age is {age.days} days",
    )


def freshness_rejection(
    assessment: FreshnessAssessment,
    *,
    policy: FreshnessPolicy = "require_fresh",
) -> str | None:
    if policy == "require_fresh":
        allowed = {"fresh"}
    elif policy == "allow_stale":
        allowed = {"fresh", "stale"}
    elif policy == "allow_unknown":
        allowed = {"fresh", "stale", "unknown"}
    else:
        raise ValueError(f"unknown freshness policy: {policy}")
    if assessment.status not in allowed:
        return f"manifest freshness={assessment.status}: {assessment.reason}"
    if assessment.cache_expired is True:
        return "manifest cache TTL expired; re-fetch before selection"
    return None


def assess_claim_freshness(
    manifest: Mapping,
    claim_path: str,
    *,
    now: datetime | None = None,
    fetched_at: datetime | None = None,
) -> FreshnessAssessment:
    """Assess one mutable claim, falling back to manifest-level provenance.

    Producers may publish field evidence under
    `extensions.io.github.ye-yi7.asm.claim-evidence`. This keeps the stable v0.3
    schema extensible while allowing a CLI surface to refresh independently of
    pricing or quality facts.
    """
    extensions = manifest.get("extensions") or {}
    evidence_map = extensions.get(CLAIM_EVIDENCE_EXTENSION) or {}
    evidence = evidence_map.get(claim_path)
    if not isinstance(evidence, Mapping):
        return assess_manifest_freshness(manifest, now=now, fetched_at=fetched_at)
    synthetic = dict(manifest)
    synthetic["provenance"] = {
        "source_url": evidence.get("source_url"),
        "last_verified_at": evidence.get("last_verified_at"),
        "verification_status": evidence.get("verification_status"),
    }
    if isinstance(evidence.get("ttl"), int):
        synthetic["ttl"] = evidence["ttl"]
    return assess_manifest_freshness(synthetic, now=now, fetched_at=fetched_at)


def selection_claim_freshness(
    manifest: Mapping,
    *,
    claim_paths: tuple[str, ...] = (
        "capabilities",
        "invocation",
        "operational_constraints",
        "pricing",
        "quality",
        "sla",
        "data_governance",
    ),
    now: datetime | None = None,
) -> dict[str, FreshnessAssessment]:
    return {
        path: assess_claim_freshness(manifest, path, now=now)
        for path in claim_paths
    }


@dataclass(frozen=True)
class InvocationSurface:
    """One independently selectable GUI, CLI, API, MCP, or SDK surface."""

    provider_id: str
    service_id: str
    version: str
    interface: str
    reach: str

    def to_dict(self) -> dict:
        return asdict(self)


def invocation_surface(manifest: Mapping) -> InvocationSurface:
    service_id = str(manifest.get("service_id") or "")
    if not service_id or "/" not in service_id:
        raise ValueError("service_id must identify provider/service")
    provider_id = service_id.split("/", 1)[0]
    version = service_id.rsplit("@", 1)[1] if "@" in service_id else "unversioned"
    invocation = manifest.get("invocation") or {}
    interface = str(invocation.get("interface") or "unknown")
    reach = str(invocation.get("reach") or "unknown")
    return InvocationSurface(provider_id, service_id, version, interface, reach)


__all__ = [
    "CLAIM_EVIDENCE_EXTENSION",
    "FreshnessAssessment",
    "FreshnessPolicy",
    "InvocationSurface",
    "assess_claim_freshness",
    "assess_manifest_freshness",
    "freshness_rejection",
    "invocation_surface",
    "parse_timestamp",
    "selection_claim_freshness",
]
