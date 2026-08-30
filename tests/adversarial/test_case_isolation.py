"""Case-isolation adversarial tests (T063, spec scenario 11).

Cross-tenant isolation is N/A for the single-tenant MVP (plan.md scope);
case isolation is the enforced boundary in this feature.
"""

from __future__ import annotations

from tests.conftest import auth


def _investigate(client, headers, alert_id="ALERT-1001"):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": alert_id}})
    return r.json()["case_id"]


def test_no_cross_case_content_in_reports(client, headers):
    """Spec scenario 11: two unrelated investigations share nothing."""
    a = _investigate(client, headers, "ALERT-1001")
    b = _investigate(client, headers, "ALERT-2001")
    report_a = client.get(f"/cases/{a}/report", headers=headers).json()["content"]
    report_b = client.get(f"/cases/{b}/report", headers=headers).json()["content"]
    assert report_a["case_id"] == a and report_b["case_id"] == b
    # No entity/user bleed between cases
    ids_a = {e["identifier"] for e in report_a["affected_entities"]}
    ids_b = {e["identifier"] for e in report_b["affected_entities"]}
    assert "a.smith" not in ids_a
    assert "j.doe" not in ids_b


def test_claim_from_other_case_not_accessible(client, headers):
    a = _investigate(client, headers, "ALERT-1001")
    b = _investigate(client, headers, "ALERT-2001")
    report_a = client.get(f"/cases/{a}/report", headers=headers).json()["content"]
    claim_a = report_a["findings"][0]["claim_id"]
    # Requesting case A's claim through case B is denied (403-safe)
    r = client.get(f"/cases/{b}/claims/{claim_a}/evidence", headers=headers)
    assert r.status_code == 403


def test_other_analyst_cannot_access_case_at_all(client, headers):
    a = _investigate(client, headers)
    mallory = auth("mallory")
    for path in (f"/cases/{a}", f"/cases/{a}/report", f"/cases/{a}/audit",
                 f"/cases/{a}/audit/verify"):
        assert client.get(path, headers=mallory).status_code == 403
    assert client.post(f"/cases/{a}/feedback", headers=mallory,
                       json={"rating": "useful"}).status_code == 403
    assert client.post(f"/cases/{a}/cancel", headers=mallory).status_code == 403


def test_audit_streams_are_case_scoped(client, headers):
    a = _investigate(client, headers, "ALERT-1001")
    b = _investigate(client, headers, "ALERT-2001")
    audit_b = client.get(f"/cases/{b}/audit", headers=headers).text
    assert a not in audit_b  # case A's ID never appears in case B's audit


def test_explicit_link_requires_access_to_both(client, headers):
    a = _investigate(client, headers)
    b = _investigate(client, auth("bob", ["alert_source"]), "ALERT-2001")
    # alice cannot link to bob's case
    r = client.post(f"/cases/{a}/links", headers=headers,
                    json={"other_case_id": b, "reason": "related"})
    assert r.status_code == 403
