"""Tests for the shared tool selector (library_select) and the hosted select API."""
from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from library_select import load_library, monthly_cost, select  # noqa: E402


def test_library_loads_and_validates_shape():
    lib = load_library()
    assert len(lib) >= 30
    assert all("service_id" in m and "taxonomy" in m for m in lib)


def test_local_device_tools_filtered_for_cloud_agent():
    r = select("store a study plan", taxonomy="tool.productivity.task_management",
               agent_reach="cloud", user_platform="windows",
               required_functions=["reminders", "recurring_tasks"])
    assert r["selected"] is not None
    rejected_names = {x["service"] for x in r["rejected"]}
    assert "Things 3" in rejected_names and "Apple Reminders" in rejected_names


def test_booking_surfaces_critical_risk_and_approval():
    r = select("book a flight", taxonomy="tool.booking.travel",
               agent_reach="cloud", user_platform="windows",
               required_functions=["flight_search", "flight_order_create"],
               require_approval_for=["financial_charge"])
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


def test_monthly_cost_free_tier_is_zero():
    lib = load_library()
    todoist = next(m for m in lib if m["service_id"].startswith("todoist/"))
    assert monthly_cost(todoist) == 0.0


def test_selection_receipt_shape_and_evidence_digests():
    from library_select import manifest_digest

    r = select("book a flight", taxonomy="tool.booking.travel",
               agent_reach="cloud", user_platform="windows",
               required_functions=["flight_search", "flight_order_create"],
               require_approval_for=["financial_charge"], receipt=True)
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
    # the operational policy is in the receipt (audit before invocation)
    assert rec["approval_required"] is True and rec["risk_class"] == "critical"


def test_receipt_absent_by_default():
    r = select("book a flight", taxonomy="tool.booking.travel",
               required_functions=["flight_search"])
    assert "receipt" not in r


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
        r = json.loads(urllib.request.urlopen(req).read())
        assert r["selected"] is not None and r["risk_class"] == "critical"
        assert r["receipt"]["receipt_type"] == "selection"
        assert all(e["manifest_digest"].startswith("sha256:") for e in r["receipt"]["evidence"])

        bad = urllib.request.Request(f"http://127.0.0.1:{port}/select", data=b"{}",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(bad)
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
