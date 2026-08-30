"""End-to-end investigation flow (T023, spec scenarios 1, 3, 9)."""

from __future__ import annotations


def _investigate(client, headers, alert_id="ALERT-1001"):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": alert_id}})
    assert r.status_code == 201
    return r.json()


def test_full_investigation_completes(client, headers):
    body = _investigate(client, headers)
    assert body["status"] == "completed"
    assert body["workflow_state"] == "COMPLETE"

    report = client.get(f"/cases/{body['case_id']}/report", headers=headers).json()
    content = report["content"]
    assert report["verified"] is True
    assert report["report_kind"] == "complete"
    # Timeline is chronologically ordered
    times = [t["event_at"] for t in content["timeline"] if t["event_at"]]
    assert times == sorted(times)
    # Entities extracted (FR-014)
    types = {e["entity_type"] for e in content["affected_entities"]}
    assert "endpoint" in types and "user" in types and "process" in types
    # Every supported material finding has evidence (FR-007 / SC-001)
    for f in content["findings"]:
        if f["support_status"] == "supported":
            assert f["supporting_evidence_ids"]
    assert content["hypotheses"]
    assert content["data_sources_consulted"]


def test_isolated_case_created(client, headers):
    a = _investigate(client, headers)
    b = _investigate(client, headers)
    assert a["case_id"] != b["case_id"]
    # Case A's report references only its own case
    report_a = client.get(f"/cases/{a['case_id']}/report", headers=headers).json()
    assert report_a["content"]["case_id"] == a["case_id"]


def test_inconclusive_marked_not_fabricated(client, headers):
    """ALERT-2001 (impossible travel) — FakeModel returns only inconclusive
    hypotheses; report must mark them inconclusive, not invent support."""
    body = _investigate(client, headers, alert_id="ALERT-2001")
    report = client.get(f"/cases/{body['case_id']}/report", headers=headers).json()
    content = report["content"]
    hyp_evals = {h["evaluation"] for h in content["hypotheses"]}
    assert "inconclusive" in hyp_evals
    # Recommended next queries present for inconclusive hypotheses (spec scenario 9)
    assert content["recommended_queries"]
    # No inference claim marked supported without evidence
    for f in content["findings"]:
        if f["claim_type"] == "inference" and f["support_status"] == "supported":
            assert f["supporting_evidence_ids"]


def test_terminal_status_always_present(client, headers):
    body = _investigate(client, headers)
    summary = client.get(f"/cases/{body['case_id']}", headers=headers).json()
    assert summary["status"] in ("completed", "partially_completed", "denied",
                                 "failed_safely", "cancelled", "budget_exhausted")
