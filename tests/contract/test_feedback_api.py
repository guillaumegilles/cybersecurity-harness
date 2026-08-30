"""Feedback API contract tests (T051)."""

from __future__ import annotations


def _case(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    return r.json()["case_id"]


def test_feedback_success(client, headers):
    case_id = _case(client, headers)
    r = client.post(f"/cases/{case_id}/feedback", headers=headers,
                    json={"rating": "useful", "corrections": "timeline entry 2 is benign"})
    assert r.status_code == 201
    assert r.json()["rating"] == "useful"


def test_feedback_invalid_rating_422(client, headers):
    case_id = _case(client, headers)
    r = client.post(f"/cases/{case_id}/feedback", headers=headers,
                    json={"rating": "amazing"})
    assert r.status_code == 422


def test_feedback_unknown_case_403(client, headers):
    r = client.post("/cases/nope/feedback", headers=headers, json={"rating": "useful"})
    assert r.status_code == 403
