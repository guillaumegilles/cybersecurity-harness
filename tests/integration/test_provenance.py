"""Provenance integration tests (T033, US2 scenarios)."""

from __future__ import annotations


def _case_with_report(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    report = client.get(f"/cases/{case_id}/report", headers=headers).json()
    return case_id, report["content"]


def test_material_conclusion_provenance(client, headers):
    case_id, content = _case_with_report(client, headers)
    supported = [f for f in content["findings"] if f["support_status"] == "supported"]
    assert supported
    claim_id = supported[0]["claim_id"]
    prov = client.get(f"/cases/{case_id}/claims/{claim_id}/evidence", headers=headers).json()
    assert prov["evidence"]
    for ev in prov["evidence"]:
        assert ev["source"]
        assert ev["collected_at"]
        assert ev["trust_classification"] in ("direct_observation", "correlated",
                                              "analyst_provided", "unverified_external")
        assert ev["relationship"] in ("supports", "contradicts", "inconclusive")


def test_direct_observation_has_source_record_id(client, headers):
    case_id, content = _case_with_report(client, headers)
    obs = [f for f in content["findings"] if f["claim_type"] == "direct_observation"]
    assert obs
    prov = client.get(f"/cases/{case_id}/claims/{obs[0]['claim_id']}/evidence",
                      headers=headers).json()
    assert any(ev["source_record_id"] for ev in prov["evidence"])


def test_inference_distinguished_from_observation(client, headers):
    """FR-010: inference never presented as directly observed fact."""
    case_id, content = _case_with_report(client, headers)
    types = {f["claim_type"] for f in content["findings"]}
    assert "inference" in types and "direct_observation" in types
    for f in content["findings"]:
        prov = client.get(f"/cases/{case_id}/claims/{f['claim_id']}/evidence",
                          headers=headers).json()
        assert prov["claim"]["claim_type"] == f["claim_type"]
