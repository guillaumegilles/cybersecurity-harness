"""Audit API contract tests (T041)."""

from __future__ import annotations

from tests.conftest import auth


def _case(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    return r.json()["case_id"]


def test_audit_listing_schema(client, headers):
    case_id = _case(client, headers)
    r = client.get(f"/cases/{case_id}/audit", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == case_id
    assert body["events"]
    for ev in body["events"]:
        assert {"sequence", "event_type", "actor", "payload", "prev_hash",
                "event_hash", "occurred_at"} <= set(ev)
    seqs = [e["sequence"] for e in body["events"]]
    assert seqs == sorted(seqs)


def test_audit_filtering(client, headers):
    case_id = _case(client, headers)
    r = client.get(f"/cases/{case_id}/audit?event_type=state_transition", headers=headers)
    assert all(e["event_type"] == "state_transition" for e in r.json()["events"])
    r2 = client.get(f"/cases/{case_id}/audit?after_sequence=5", headers=headers)
    assert all(e["sequence"] > 5 for e in r2.json()["events"])


def test_audit_verify_intact(client, headers):
    case_id = _case(client, headers)
    r = client.get(f"/cases/{case_id}/audit/verify", headers=headers)
    body = r.json()
    assert body["intact"] is True
    assert body["first_broken_sequence"] is None
    assert body["events_checked"] > 0


def test_audit_unauthorized_403(client, headers):
    case_id = _case(client, headers)
    assert client.get(f"/cases/{case_id}/audit", headers=auth("mallory")).status_code == 403
