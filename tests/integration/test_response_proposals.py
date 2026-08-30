"""Response-action proposal tests (T038, FR-016)."""

from __future__ import annotations


def test_proposals_present_and_not_executed(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    proposals = report["content"]["response_action_proposals"]
    assert proposals  # ALERT-1001 has a supported hypothesis -> proposals generated
    for p in proposals:
        assert p["proposal_only"] is True
        assert p["affected_resources"]
        assert p["expected_impact"]
        assert p["risk"]
        assert p["rollback_method"]
        assert "PROPOSAL" in p["action_description"]

    # Nothing was executed: no tool operation exists for any response action.
    audit = client.get(f"/cases/{case_id}/audit", headers=headers).json()
    tool_events = [e for e in audit["events"] if e["event_type"] in ("tool_result",)]
    for e in tool_events:
        assert "isolate" not in str(e["payload"]).lower()
        assert "block" not in str(e["payload"]).lower()


def test_no_proposals_without_supported_hypothesis(client, headers):
    """ALERT-2001 yields only inconclusive hypotheses -> no proposals."""
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-2001"}})
    case_id = r.json()["case_id"]
    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    assert report["content"]["response_action_proposals"] == []
