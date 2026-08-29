"""Tests for the shared tool selector (library_select) and the hosted select API."""
from __future__ import annotations

import json
import math
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library_select import (  # noqa: E402
    estimate_monthly_cost,
    load_library,
    monthly_cost,
    select,
)


def test_library_loads_and_validates_shape():
    lib = load_library()
    assert len(lib) >= 30
    assert all("service_id" in m and "taxonomy" in m for m in lib)


def test_local_device_tools_filtered_for_cloud_agent():
    r = select("store a study plan", taxonomy="tool.productivity.task_management",
               agent_reach="cloud", user_platform="windows",
               required_functions=["reminders", "recurring_tasks"],
               fallback_policy="capability_breadth")
    assert r["selected"] is not None
    rejected_names = {x["service"] for x in r["rejected"]}
    assert "Things 3" in rejected_names and "Apple Reminders" in rejected_names


def test_booking_surfaces_critical_risk_and_approval():
    r = select("book a flight", taxonomy="tool.booking.travel",
               agent_reach="cloud", user_platform="windows",
               required_functions=["flight_search", "flight_order_create"],
               require_approval_for=["financial_charge"],
               fallback_policy="capability_breadth")
    assert r["selected"] is not None
    assert r["risk_class"] == "critical"
    assert r["approval_required"] is True
    assert "financial_charge" in r["side_effects"]


def test_agent_completable_setup_gate():
    r = select("property data", taxonomy="tool.data.real_estate",
               agent_reach="cloud", user_platform="windows",
               required_functions=["real_estate_data"],
               require_agent_completable_setup=True)
    assert r["selected"]["display_name"] == "US Census Bureau Data API"
    reasons = " ".join(x["reason"] for x in r["rejected"])
    assert "setup not agent-completable" in reasons


def test_unstructured_free_tier_is_not_treated_as_known_zero():
    lib = load_library()
    todoist = next(m for m in lib if m["service_id"].startswith("todoist/"))
    estimate = estimate_monthly_cost(todoist)
    assert estimate.status in {"partial", "unknown"}
    assert estimate.monthly_total is None
    assert "free_tier_allowance" in estimate.unknown_dimensions
    assert math.isinf(monthly_cost(todoist))


def test_task_only_request_is_explicitly_under_specified():
    result = select("find me the best tool")
    assert result["selection_status"] == "under_specified"
    assert result["task_interpreted"] is False
    assert result["selected"] is None
    assert "does not interpret task text" in result["reason"]


def test_selection_receipt_shape_and_evidence_digests():
    from library_select import manifest_digest

    r = select("book a flight", taxonomy="tool.booking.travel",
               agent_reach="cloud", user_platform="windows",
               required_functions=["flight_search", "flight_order_create"],
               require_approval_for=["financial_charge"], receipt=True,
               selection_profile="legacy-0.5.2")
    rec = r["receipt"]
    assert rec["receipt_type"] == "selection" and rec["receipt_version"] == "0.1"
    assert rec["request"]["required_functions"] == ["flight_search", "flight_order_create"]
    # evidence covers the full considered pool (taxonomy match), digests deterministic
    lib = load_library()
    pool = [m for m in lib if m.get("taxonomy") == "tool.booking.travel"]
    assert {e["service_id"] for e in rec["evidence"]} == {m["service_id"] for m in pool}
    for e, m in zip(sorted(rec["evidence"], key=lambda x: x["service_id"]),
                    sorted(pool, key=lambda x: x["service_id"])):
        assert e["manifest_digest"] == manifest_digest(m)
        assert e["manifest_digest"].startswith("sha256:")
    assert rec["selector"]["name"] == "asm-protocol/0.5.1"
    assert r["selection_status"] == "selected"
    assert rec["selected"] is not None
    assert r["selected"] == rec["selected"]
    assert rec["approval_required"] is True and rec["risk_class"] == "critical"


def test_receipt_absent_by_default():
    r = select("book a flight", taxonomy="tool.booking.travel",
               required_functions=["flight_search"])
    assert "receipt" not in r


def test_current_selector_cannot_emit_legacy_receipt_contract():
    with pytest.raises(ValueError, match="cannot represent the v0.6"):
        select(
            "book a flight",
            taxonomy="tool.booking.travel",
            required_functions=["flight_search", "flight_order_create"],
            receipt=True,
        )


def test_legacy_profile_rejects_new_cost_inputs():
    with pytest.raises(ValueError, match="cannot use workload or fallback_policy"):
        select(
            "book a flight",
            taxonomy="tool.booking.travel",
            required_functions=["flight_search", "flight_order_create"],
            workload={"monthly_units": {"booking": 12}},
            selection_profile="legacy-0.5.2",
        )


def test_select_api_endpoints():
    import asm_select_api as api

    srv = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        landing = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode()
        assert "The selection layer for agents" in landing

        h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz").read())
        assert h["ok"] and h["tools"] >= 30

        tools = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{port}/tools?taxonomy=tool.data.real_estate").read())
        assert len(tools) == 4

        body = json.dumps({"task": "book a flight", "taxonomy": "tool.booking.travel",
                           "user_platform": "windows",
                           "required_functions": ["flight_search", "flight_order_create"],
                           "receipt": True}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/select", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req)
            assert False, "expected current selector receipt request to fail"
        except urllib.error.HTTPError as e:
            assert e.code == 400
            assert "cannot represent the v0.6" in json.loads(e.read())["error"]

        legacy_body = json.dumps({
            "task": "book a flight",
            "taxonomy": "tool.booking.travel",
            "user_platform": "windows",
            "required_functions": ["flight_search", "flight_order_create"],
            "receipt": True,
            "selection_profile": "legacy-0.5.2",
        }).encode()
        legacy_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/select",
            data=legacy_body,
            headers={"Content-Type": "application/json"},
        )
        legacy = json.loads(urllib.request.urlopen(legacy_req).read())
        assert legacy["selected"] is not None
        assert legacy["receipt"]["receipt_type"] == "selection"
        assert legacy["receipt"]["selector"]["name"] == "asm-protocol/0.5.1"

        bad = urllib.request.Request(f"http://127.0.0.1:{port}/select", data=b"{}",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(bad)
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400

        task_only = urllib.request.Request(
            f"http://127.0.0.1:{port}/select",
            data=json.dumps({"task": "pick the best one"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(task_only)
            assert False, "expected 422"
        except urllib.error.HTTPError as e:
            assert e.code == 422
            payload = json.loads(e.read())
            assert payload["selection_status"] == "under_specified"

        bad_workload = urllib.request.Request(
            f"http://127.0.0.1:{port}/select",
            data=json.dumps({
                "task": "book a flight",
                "taxonomy": "tool.booking.travel",
                "workload": {"surprise": 1},
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(bad_workload)
            assert False, "expected 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400

        # .well-known/asm catalog: one generated_at, per-manifest links
        cat = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{port}/.well-known/asm").read())
        assert cat["count"] >= 30 and cat["generated_at"]
        assert all("service_id" in e and e["url"].startswith("/manifest/")
                   for e in cat["manifests"])

        # follow a catalog link to a full manifest
        first = cat["manifests"][0]
        man = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{port}{first['url']}").read())
        assert man["service_id"] == first["service_id"]
        assert man.get("asm_version") == "0.3"

        # AI Catalog document (schema v1.0): namespaced extension, URL resolvable
        aic = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{port}/.well-known/ai-catalog.json").read())
        assert aic["specVersion"] == "1.0"
        assert len(aic["entries"]) >= 30
        import re as _re
        urn = _re.compile(r"^urn:air:[a-zA-Z0-9.-]+(?::[a-zA-Z0-9._:-]+)?:[a-zA-Z0-9._-]+$")
        for e in aic["entries"]:
            assert urn.match(e["identifier"]), e["identifier"]
            assert e["type"] == "application/asm+json" and "mediaType" not in e
        e = aic["entries"][0]
        ext = e["extensions"]["io.github.ye-yi7.asm.selection"]
        assert ext["asm:taxonomy"]
        assert all(isinstance(v, (str, int, float, bool)) or v is None
                   for v in ext.values())
        assert e["url"].startswith(f"http://127.0.0.1:{port}/manifest/")
        man2 = json.loads(urllib.request.urlopen(e["url"]).read())
        assert man2["service_id"] in e["url"]
    finally:
        srv.shutdown()
