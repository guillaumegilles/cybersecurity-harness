"""Feedback integration tests (T052, US6)."""

from __future__ import annotations


def _case(client, headers, alert_id="ALERT-1001"):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": alert_id}})
    return r.json()["case_id"]


def test_feedback_recorded_and_audited(client, headers):
    case_id = _case(client, headers)
    r = client.post(f"/cases/{case_id}/feedback", headers=headers,
                    json={"rating": "partially_useful",
                          "corrections": "second hypothesis is more likely",
                          "final_disposition": "true positive, contained manually"})
    assert r.status_code == 201
    audit = client.get(f"/cases/{case_id}/audit?event_type=feedback_recorded",
                       headers=headers).json()
    assert audit["events"]
    assert audit["events"][0]["payload"]["rating"] == "partially_useful"


def test_feedback_case_isolated(client, headers):
    a = _case(client, headers)
    b = _case(client, headers)
    client.post(f"/cases/{a}/feedback", headers=headers, json={"rating": "useful"})
    audit_b = client.get(f"/cases/{b}/audit?event_type=feedback_recorded",
                         headers=headers).json()
    assert audit_b["events"] == []
