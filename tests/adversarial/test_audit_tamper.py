"""Audit-tamper adversarial tests (T043, Constitution VII)."""

from __future__ import annotations

import pytest

from harness.audit.service import AuditService
from harness.policy.rules import is_prohibited


def test_audit_service_has_no_mutation_methods():
    public = {n for n in dir(AuditService) if not n.startswith("_")}
    assert public == {"append", "list_events", "verify_chain"}


def test_audit_operations_prohibited_by_policy():
    for op in ("modify_audit", "delete_audit", "suppress_audit"):
        assert is_prohibited(op)


def test_direct_db_tamper_detected(session):
    audit = AuditService(session)
    for i in range(4):
        audit.append("case-t", "state_transition", "orch", {"i": i})
    session.commit()
    events = audit.list_events("case-t")
    # Attacker rewrites an event directly in the DB
    events[2].payload = {"i": "REWRITTEN"}
    session.commit()
    result = audit.verify_chain("case-t")
    assert result["intact"] is False
    assert result["first_broken_sequence"] == 3


def test_deletion_tamper_detected(session):
    audit = AuditService(session)
    for i in range(4):
        audit.append("case-d", "state_transition", "orch", {"i": i})
    session.commit()
    events = audit.list_events("case-d")
    session.delete(events[1])  # attacker deletes a middle event
    session.commit()
    result = audit.verify_chain("case-d")
    assert result["intact"] is False


def test_investigation_audit_endpoint_readonly(client):
    """No HTTP mutation path for audit records."""
    paths = client.app.openapi()["paths"]
    audit_paths = {p: ops for p, ops in paths.items() if "audit" in p}
    assert audit_paths
    for p, ops in audit_paths.items():
        assert set(ops) <= {"get", "head"}, f"audit mutation possible: {p} {set(ops)}"
