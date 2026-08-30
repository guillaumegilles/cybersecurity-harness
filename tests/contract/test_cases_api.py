"""Cases API contract tests (T021)."""

from __future__ import annotations

from tests.conftest import auth


def test_create_case_connected_source(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"case_id", "status", "workflow_state", "limits"}
    assert body["status"] in ("completed", "partially_completed", "denied",
                              "failed_safely", "cancelled", "budget_exhausted")


def test_create_case_analyst_submitted(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "analyst_submitted",
                                    "content": {"description": "manual alert", "host": "WS-099"}}})
    assert r.status_code == 201


def test_create_case_missing_alert_id_400(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source"}})
    assert r.status_code == 400
    assert "error" in r.json()


def test_create_case_invalid_limit_override_400(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"},
                          "limit_overrides": {"max_tool_operations": 999999}})
    assert r.status_code == 400


def test_unauthenticated_401(client):
    r = client.post("/cases", json={"alert": {"origin": "connected_source", "alert_id": "X"}})
    assert r.status_code == 401


def test_get_case_other_analyst_403(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    r2 = client.get(f"/cases/{case_id}", headers=auth("mallory"))
    assert r2.status_code == 403


def test_get_nonexistent_case_same_as_unauthorized(client, headers):
    """FR-019: identical response for missing vs unauthorized."""
    r = client.get("/cases/does-not-exist", headers=headers)
    assert r.status_code == 403


def test_rerun_same_alert_creates_new_case(client, headers):
    r1 = client.post("/cases", headers=headers,
                     json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    r2 = client.post("/cases", headers=headers,
                     json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    assert r1.json()["case_id"] != r2.json()["case_id"]


def test_cancel_terminal_case_409(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    r2 = client.post(f"/cases/{case_id}/cancel", headers=headers)
    assert r2.status_code == 409
