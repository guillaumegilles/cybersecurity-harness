"""Report schema contract tests (T022, FR-013)."""

from __future__ import annotations

from harness.storage.schemas import ReportContent

REQUIRED_SECTIONS = {
    "case_id", "alert_id", "status", "alert_summary", "scope", "timeline",
    "affected_entities", "findings", "hypotheses",
    "contradicting_or_inconclusive_evidence", "missing_information",
    "severity_assessment", "recommended_queries", "response_action_proposals",
    "limitations", "data_sources_consulted", "tool_operations",
    "started_at", "completed_at",
}


def _get_report(client, headers, alert_id="ALERT-1001"):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": alert_id}})
    case_id = r.json()["case_id"]
    return client.get(f"/cases/{case_id}/report", headers=headers).json()


def test_report_contains_all_fr013_sections(client, headers):
    report = _get_report(client, headers)
    assert REQUIRED_SECTIONS <= set(report["content"].keys())
    # Validates against the Pydantic schema
    ReportContent(**report["content"])


def test_findings_have_confidence_and_type(client, headers):
    report = _get_report(client, headers)
    for f in report["content"]["findings"]:
        assert f["confidence"] in ("high", "medium", "low", "inconclusive")
        assert f["claim_type"] in ("direct_observation", "correlation", "inference",
                                   "analyst_provided", "unverified_external")


def test_proposals_marked_proposal_only(client, headers):
    report = _get_report(client, headers)
    for p in report["content"]["response_action_proposals"]:
        assert p["proposal_only"] is True


def test_markdown_rendering(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    r2 = client.get(f"/cases/{case_id}/report?format=markdown", headers=headers)
    assert r2.status_code == 200
    assert "# Investigation Report" in r2.text
