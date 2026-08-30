"""Foundational policy tests (T020) + read-only enforcement (T036)."""

from __future__ import annotations

import pytest

from harness.audit.service import AuditService
from harness.orchestrator.case_service import create_case
from harness.policy.engine import AuthorizationRequest, PolicyEngine
from harness.policy.rules import PROHIBITED_OPERATIONS
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest
from harness.tools.registry import REGISTERED_OPERATIONS


@pytest.fixture()
def case(session):
    c = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    session.commit()
    return c


def _req(case, **kw) -> AuthorizationRequest:
    defaults = dict(
        agent_identity=case.agent_execution_id,
        analyst_id="alice",
        analyst_sources=("alert_source", "endpoint_telemetry", "identity_context"),
        case_id=case.id,
        operation="alert_source.get_alert",
        tool_name="alert_source.get_alert",
        target_source="alert_source",
        target_resource="ALERT-1001",
        registered_operations=REGISTERED_OPERATIONS,
        budget_ok=True,
        budget_snapshot={},
    )
    defaults.update(kw)
    return AuthorizationRequest(**defaults)


def test_allow_registered_authorized(session, case):
    engine = PolicyEngine(session, AuditService(session))
    d = engine.authorize(_req(case))
    assert d.decision == "allow"


def test_deny_by_default_unregistered(session, case):
    engine = PolicyEngine(session, AuditService(session))
    d = engine.authorize(_req(case, operation="unknown.op", tool_name="unknown.op"))
    assert d.decision == "deny"
    assert d.reason == "operation_not_registered"


def test_ambiguity_denied(session, case):
    engine = PolicyEngine(session, AuditService(session))
    d = engine.authorize(_req(case, agent_identity=""))
    assert d.decision == "deny"
    assert d.reason == "authorization_context_incomplete"


def test_unauthorized_source_opaque_denial(session, case):
    """FR-019: denial must not reveal whether the data exists."""
    engine = PolicyEngine(session, AuditService(session))
    d = engine.authorize(_req(case, analyst_sources=("alert_source",),
                              target_source="endpoint_telemetry",
                              operation="endpoint_telemetry.get_events",
                              tool_name="endpoint_telemetry.get_events"))
    assert d.decision == "deny"
    assert d.reason == "not_authorized"
    assert "exist" not in d.reason and "found" not in d.reason


def test_budget_exhausted_denied(session, case):
    engine = PolicyEngine(session, AuditService(session))
    d = engine.authorize(_req(case, budget_ok=False))
    assert d.decision == "deny"


@pytest.mark.parametrize("op", sorted(PROHIBITED_OPERATIONS))
def test_every_prohibited_operation_denied(session, case, op):
    """T036: every FR-017 prohibited operation class is denied and recorded."""
    engine = PolicyEngine(session, AuditService(session))
    d = engine.authorize(_req(case, operation=op, tool_name=op))
    assert d.decision == "deny"
    assert d.reason == "operation_prohibited_readonly_policy"
    # Denial recorded in audit (FR-018)
    events = AuditService(session).list_events(case.id, event_type="policy_denial")
    assert any(e.payload.get("operation") == op for e in events)


def test_denials_are_recorded_in_audit(session, case):
    engine = PolicyEngine(session, AuditService(session))
    engine.authorize(_req(case, operation="isolate_endpoint", tool_name="isolate_endpoint"))
    audit = AuditService(session)
    decisions = audit.list_events(case.id, event_type="authorization_decision")
    denials = audit.list_events(case.id, event_type="policy_denial")
    assert decisions and denials
