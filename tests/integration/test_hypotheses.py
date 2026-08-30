"""Hypothesis comparison test (T060, US8, FR-015)."""

from __future__ import annotations


def test_alternative_hypotheses_with_confirm_reject_evidence(client, headers):
    """ALERT-2001 (impossible travel) has two plausible explanations."""
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-2001"}})
    case_id = r.json()["case_id"]
    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    hyps = report["content"]["hypotheses"]
    assert len(hyps) >= 2  # alternatives listed
    for h in hyps:
        assert h["evaluation"] in ("supported", "rejected", "inconclusive")
        assert h["confirming_evidence_needed"]  # what would confirm it
    statements = [h["statement"].lower() for h in hyps]
    assert any("compromise" in s or "credential" in s for s in statements)
    assert any("vpn" in s for s in statements)
