"""Audit hash-chain tests (T020, FR-028/FR-030)."""

from __future__ import annotations

import pytest

from harness.audit.service import AuditError, AuditService


def test_chain_intact(session):
    audit = AuditService(session)
    for i in range(5):
        audit.append("case-1", "state_transition", "orchestrator", {"i": i})
    session.commit()
    result = audit.verify_chain("case-1")
    assert result["intact"] is True
    assert result["events_checked"] == 5


def test_tampering_detected(session):
    audit = AuditService(session)
    for i in range(3):
        audit.append("case-2", "state_transition", "orchestrator", {"i": i})
    session.commit()
    events = audit.list_events("case-2")
    events[1].payload = {"i": 999}  # simulate direct DB tampering
    session.commit()
    result = audit.verify_chain("case-2")
    assert result["intact"] is False
    assert result["first_broken_sequence"] == 2


def test_unknown_event_type_rejected(session):
    audit = AuditService(session)
    with pytest.raises(AuditError):
        audit.append("case-3", "not_a_real_event", "x", {})


def test_ordering_sequential_per_case(session):
    audit = AuditService(session)
    audit.append("case-4", "case_created", "alice", {})
    audit.append("case-5", "case_created", "bob", {})
    audit.append("case-4", "scope_set", "system", {})
    events4 = audit.list_events("case-4")
    assert [e.sequence for e in events4] == [1, 2]


def test_secret_redaction_in_payload(session):
    audit = AuditService(session)
    ev = audit.append("case-6", "tool_result", "invoker",
                      {"password": "hunter2", "note": "AKIA1234567890ABCDEF"})
    assert ev.payload["password"] == "[REDACTED]"
    assert ev.payload["note"] == "[REDACTED]"


def test_no_mutation_api_on_audit_service():
    """The audit service exposes no update/delete methods (FR-030)."""
    public = {n for n in dir(AuditService) if not n.startswith("_")}
    assert public == {"append", "list_events", "verify_chain"}
