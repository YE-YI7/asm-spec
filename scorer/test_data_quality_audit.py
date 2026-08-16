from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("audit_manifest_data", ROOT / "tools" / "audit_manifest_data.py")
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def test_freshness_boundaries_and_invalid_values():
    as_of = datetime(2026, 8, 16, tzinfo=timezone.utc)
    assert audit.freshness_status("2026-07-17T00:00:00Z", as_of) == ("fresh", 30)
    assert audit.freshness_status("2026-07-16T00:00:00Z", as_of) == ("stale", 31)
    assert audit.freshness_status("2026-05-18T00:00:00Z", as_of) == ("stale", 90)
    assert audit.freshness_status("2026-05-17T00:00:00Z", as_of) == ("expired", 91)
    assert audit.freshness_status(None, as_of) == ("unknown", None)
    assert audit.freshness_status("not-a-date", as_of) == ("invalid", None)


def test_repository_report_exposes_snapshot_age_and_verification_distribution():
    report = audit.build_report(ROOT, datetime(2026, 8, 16, 23, 59, 59, tzinfo=timezone.utc))
    assert report["summary"]["entries"] == 105
    assert report["summary"]["schema"] == {"valid": 105}
    assert report["collections"]["manifests"]["freshness"] == {"expired": 75}
    assert report["collections"]["manifests"]["verification"] == {
        "manual_verified": 5,
        "self_reported": 70,
    }
    assert report["collections"]["library"]["freshness"] == {"stale": 30}
    assert report["collections"]["library"]["verification"] == {
        "manual_verified": 10,
        "self_reported": 20,
    }


def test_403_is_access_restricted_not_dead():
    error = HTTPError("https://example.com", 403, "Forbidden", {}, None)
    with patch.object(audit, "urlopen", side_effect=error):
        result = audit.check_source_url("https://example.com")
    assert result.status == "access_restricted"
    assert result.http_status == 403


def test_machine_report_is_json_serializable():
    report = audit.build_report(ROOT, datetime(2026, 8, 16, tzinfo=timezone.utc))
    json.dumps(report)
