"""Budget exhaustion + tool-failure integration tests (T055, spec scenarios 8 & 10)."""

from __future__ import annotations

from harness.connectors import endpoint_telemetry


def test_tool_operation_limit_triggers_partial_report(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"},
                          "limit_overrides": {"max_tool_operations": 1}})
    body = r.json()
    assert body["status"] == "budget_exhausted"

    case_id = body["case_id"]
    summary = client.get(f"/cases/{case_id}", headers=headers).json()
    assert "budget exhausted" in summary["termination_reason"]
    assert "max_tool_operations" in summary["termination_reason"]

    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    assert report["report_kind"] == "partial"
    assert any("terminated early" in l for l in report["content"]["limitations"])


def test_model_call_limit(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"},
                          "limit_overrides": {"max_model_calls": 1, "max_tool_operations": 3}})
    assert r.json()["status"] in ("budget_exhausted", "completed")


def test_evidence_limit_triggers_safe_stop(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"},
                          "limit_overrides": {"max_evidence_items": 1}})
    body = r.json()
    assert body["status"] == "budget_exhausted"


def test_tool_failure_identified_no_substitution(client, headers):
    """Spec scenario 8: unavailable source noted in report; nothing substituted."""
    endpoint_telemetry.AVAILABLE = False
    try:
        r = client.post("/cases", headers=headers,
                        json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
        body = r.json()
        case_id = body["case_id"]
        report = client.get(f"/cases/{case_id}/report", headers=headers).json()
        content = report["content"]
        # Unavailable evidence identified
        assert any("unavailable" in l.lower() for l in content["limitations"])
        # endpoint_telemetry not listed as consulted (no silent substitution)
        assert "endpoint_telemetry" not in content["data_sources_consulted"]
        # failure recorded in audit
        audit = client.get(f"/cases/{case_id}/audit?event_type=tool_failure",
                           headers=headers).json()
        assert audit["events"]
    finally:
        endpoint_telemetry.AVAILABLE = True
