"""Fail-safe tests (T057, FR-020/FR-033), incl. ambiguous-scope handling."""

from __future__ import annotations

from harness.connectors import alert_source
from harness.orchestrator import states
from harness.orchestrator.case_service import create_case
from harness.orchestrator.machine import NEXT_STATE, TERMINAL_STATES, State, StateMachine
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest

ALL = ("alert_source", "endpoint_telemetry", "identity_context")


def _mkcase(session, alert_id="ALERT-1001", analyst="alice"):
    return create_case(
        session, analyst,
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id=alert_id)),
    )


def test_all_failure_transitions_terminal():
    for state in NEXT_STATE:
        m = StateMachine(on_transition=lambda p, n: None)
        m.current = state
        m.fail()
        assert m.current in TERMINAL_STATES


def test_source_unavailable_fails_safely(session):
    case = _mkcase(session)
    alert_source.AVAILABLE = False
    try:
        case = states.run_investigation(session, case, ALL)
    finally:
        alert_source.AVAILABLE = True
    assert case.status == "partially_completed"
    assert case.workflow_state == State.SOURCE_UNAVAILABLE.value
    assert "unavailable" in (case.termination_reason or "").lower() or case.termination_reason


def test_no_authorized_sources_denied(session):
    """Authorization cannot be established -> denial, no expanded access."""
    case = _mkcase(session)
    case = states.run_investigation(session, case, ())
    assert case.status == "denied"
    assert case.workflow_state == State.ACCESS_DENIED.value


def test_unknown_alert_ambiguous_scope_fails_safely(session):
    """Ambiguous/unresolvable case scope: fails safely, never broadens scope (FR-033)."""
    case = _mkcase(session, alert_id="NO-SUCH-ALERT")
    case = states.run_investigation(session, case, ALL)
    assert case.status in ("partially_completed", "failed_safely")
    assert case.termination_reason


def test_failure_never_expands_authorization(session):
    """After a failure, a subsequent unauthorized op is still denied (FR-020)."""
    case = _mkcase(session, alert_id="NO-SUCH-ALERT")
    states.run_investigation(session, case, ALL)

    from harness.audit.service import AuditService
    from harness.orchestrator.budget import BudgetService
    from harness.policy.engine import PolicyEngine
    from harness.storage.repositories import CaseContext, CaseScopedRepository
    from harness.tools.invoker import ToolInvoker

    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "alice", case.agent_execution_id))
    invoker = ToolInvoker(repo, PolicyEngine(session, audit),
                          BudgetService(session, audit, case), audit, ("alert_source",))
    result = invoker.invoke("endpoint_telemetry.get_events", {"endpoint_id": "WS-042"})
    assert result.outcome == "denied"
