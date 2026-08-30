from datetime import datetime, timedelta, timezone

import pytest

from asm_protocol.freshness import (
    CLAIM_EVIDENCE_EXTENSION,
    assess_claim_freshness,
    assess_manifest_freshness,
    freshness_rejection,
    invocation_surface,
)


NOW = datetime(2026, 8, 31, tzinfo=timezone.utc)


def _manifest(days_old: int, *, ttl: int | None = None):
    value = {
        "service_id": "wecom/cli@1.2.0",
        "provenance": {
            "source_url": "https://example.test/releases",
            "last_verified_at": (NOW - timedelta(days=days_old)).isoformat(),
            "verification_status": "manual_verified",
        },
        "invocation": {"interface": "cli", "reach": "local_device"},
    }
    if ttl is not None:
        value["ttl"] = ttl
    return value


@pytest.mark.parametrize(
    ("days", "status"),
    [(5, "fresh"), (45, "stale"), (120, "expired")],
)
def test_verification_age_is_classified_independently_of_schema(days, status):
    assert assess_manifest_freshness(_manifest(days), now=NOW).status == status


def test_default_gate_refuses_stale_facts_but_explicit_policy_can_surface_them():
    assessment = assess_manifest_freshness(_manifest(45), now=NOW)
    assert "freshness=stale" in freshness_rejection(assessment)
    assert freshness_rejection(assessment, policy="allow_stale") is None


def test_cache_ttl_never_refreshes_old_verification_evidence():
    fetched = NOW - timedelta(hours=2)
    assessment = assess_manifest_freshness(
        _manifest(5, ttl=3600), now=NOW, fetched_at=fetched
    )
    assert assessment.status == "fresh"
    assert assessment.cache_expired is True
    assert "TTL expired" in freshness_rejection(assessment)


def test_cli_and_gui_are_distinct_selectable_surfaces():
    cli = invocation_surface(_manifest(5))
    gui_manifest = _manifest(5)
    gui_manifest["service_id"] = "wecom/gui@current"
    gui_manifest["invocation"] = {"interface": "gui", "reach": "local_device"}
    gui = invocation_surface(gui_manifest)
    assert cli.provider_id == gui.provider_id == "wecom"
    assert cli.service_id != gui.service_id
    assert {cli.interface, gui.interface} == {"cli", "gui"}


def test_missing_verification_is_unknown_and_refused_by_default():
    assessment = assess_manifest_freshness(
        {"service_id": "example/tool@1", "provenance": {}}, now=NOW
    )
    assert assessment.status == "unknown"
    assert freshness_rejection(assessment)


def test_cli_claim_can_refresh_independently_of_old_manifest():
    manifest = _manifest(120)
    manifest["extensions"] = {
        CLAIM_EVIDENCE_EXTENSION: {
            "invocation": {
                "source_url": "https://example.test/cli/releases",
                "last_verified_at": "2026-08-30T00:00:00Z",
                "verification_status": "manual_verified",
                "ttl": 86400,
            }
        }
    }
    assert assess_manifest_freshness(manifest, now=NOW).status == "expired"
    assert assess_claim_freshness(manifest, "invocation", now=NOW).status == "fresh"
    assert assess_claim_freshness(manifest, "pricing", now=NOW).status == "expired"
