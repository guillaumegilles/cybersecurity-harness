"""Provenance API contract tests (T032)."""

from __future__ import annotations

from tests.conftest import auth


def _completed_case(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    return r.json()["case_id"]


def test_provenance_response_schema(client, headers):
    case_id = _completed_case(client, headers)
    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    claim_id = report["content"]["findings"][0]["claim_id"]
    r = client.get(f"/cases/{case_id}/claims/{claim_id}/evidence", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"claim", "evidence", "missing_evidence"}
    assert set(body["claim"]) == {"id", "statement", "claim_type", "support_status", "confidence"}
    for ev in body["evidence"]:
        assert {"id", "relationship", "source", "source_record_id", "collected_at",
                "event_at", "trust_classification", "content"} <= set(ev)


def test_unknown_claim_403_safe(client, headers):
    case_id = _completed_case(client, headers)
    r = client.get(f"/cases/{case_id}/claims/nonexistent/evidence", headers=headers)
    assert r.status_code == 403


def test_other_analyst_claim_access_denied(client, headers):
    case_id = _completed_case(client, headers)
    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    claim_id = report["content"]["findings"][0]["claim_id"]
    r = client.get(f"/cases/{case_id}/claims/{claim_id}/evidence", headers=auth("mallory"))
    assert r.status_code == 403
