"""Audit-completeness reconstruction test (T042, FR-028/FR-029, spec scenario 12)."""

from __future__ import annotations


def test_reconstruct_investigation_from_audit(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]

    # Feedback so the feedback event also exists (post-run event coverage).
    client.post(f"/cases/{case_id}/feedback", headers=headers, json={"rating": "useful"})

    audit = client.get(f"/cases/{case_id}/audit", headers=headers).json()
    types = [e["event_type"] for e in audit["events"]]

    # All lifecycle event categories present (FR-028)
    for required in ("case_created", "scope_set", "state_transition", "source_accessed",
                     "tool_requested", "authorization_decision", "tool_result",
                     "evidence_collected", "claim_generated", "budget_consumed",
                     "report_generated", "feedback_recorded"):
        assert required in types, f"missing audit event type: {required}"

    # Ordered, gap-free sequence
    seqs = [e["sequence"] for e in audit["events"]]
    assert seqs == list(range(1, len(seqs) + 1))

    # Workflow reconstruction: transitions trace RECEIVE_ALERT -> COMPLETE
    transitions = [e["payload"] for e in audit["events"] if e["event_type"] == "state_transition"]
    assert transitions[0]["from"] == "RECEIVE_ALERT"
    assert transitions[-1]["to"] == "COMPLETE"

    # Every tool op has an authorization decision recorded before its result (FR-029)
    decision_ops = {e["payload"].get("operation")
                    for e in audit["events"] if e["event_type"] == "authorization_decision"}
    requested = {e["payload"].get("tool")
                 for e in audit["events"] if e["event_type"] == "tool_requested"}
    assert requested <= decision_ops

    # Chain intact
    verify = client.get(f"/cases/{case_id}/audit/verify", headers=headers).json()
    assert verify["intact"] is True
