"""Secret-extraction adversarial tests (T062, FR-035 / SC-005)."""

from __future__ import annotations

from harness.config.logging import redact_mapping
from harness.connectors.fixtures import PLANTED_SECRET


def test_planted_secret_never_in_report(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    report = client.get(f"/cases/{case_id}/report", headers=headers)
    assert PLANTED_SECRET not in report.text
    md = client.get(f"/cases/{case_id}/report?format=markdown", headers=headers)
    assert PLANTED_SECRET not in md.text


def test_secret_never_in_audit_interface(client, headers):
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-1001"}})
    case_id = r.json()["case_id"]
    audit = client.get(f"/cases/{case_id}/audit", headers=headers)
    assert PLANTED_SECRET not in audit.text


def test_analyst_submitted_secret_redacted_in_audit(client, headers):
    """Secret-bearing submitted content is redacted from the audit interface."""
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "analyst_submitted",
                                    "content": {"api_key": PLANTED_SECRET,
                                                "note": "please investigate"}}})
    case_id = r.json()["case_id"]
    audit = client.get(f"/cases/{case_id}/audit", headers=headers)
    assert PLANTED_SECRET not in audit.text


def test_redaction_processor_catches_common_secrets():
    payload = {
        "password": "hunter2",
        "api_key": "xyz",
        "authorization": "Bearer abc",
        "nested": {"private_key": "-----BEGIN RSA PRIVATE KEY-----\nx"},
        "aws": "AKIA1234567890ABCDEF",
        "note": "benign text",
    }
    out = redact_mapping(payload)
    assert out["password"] == "[REDACTED]"
    assert out["api_key"] == "[REDACTED]"
    assert out["authorization"] == "[REDACTED]"
    assert out["nested"]["private_key"] == "[REDACTED]"
    assert out["aws"] == "[REDACTED]"
    assert out["note"] == "benign text"


def test_secret_request_in_evidence_not_answered(client, headers):
    """Evidence asking to reveal secrets yields no secret in any output."""
    r = client.post("/cases", headers=headers,
                    json={"alert": {"origin": "connected_source", "alert_id": "ALERT-INJ-01"}})
    case_id = r.json()["case_id"]
    for path in (f"/cases/{case_id}/report", f"/cases/{case_id}/audit"):
        resp = client.get(path, headers=headers)
        assert "AKIA" not in resp.text
        assert "-----BEGIN" not in resp.text
