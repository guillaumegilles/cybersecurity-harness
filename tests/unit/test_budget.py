"""Budget enforcement tests (T020, FR-031)."""

from __future__ import annotations

import pytest

from harness.audit.service import AuditService
from harness.config.settings import BudgetLimits
from harness.orchestrator.budget import BudgetExceeded, BudgetService
from harness.orchestrator.case_service import create_case
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest


def _case(session, overrides=None):
    return create_case(
        session, "alice",
        CreateCaseRequest(
            alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001"),
            limit_overrides=overrides,
        ),
    )


def test_limits_cannot_be_unbounded():
    with pytest.raises(ValueError):
        BudgetLimits(max_tool_operations=10_000_000)
    with pytest.raises(ValueError):
        BudgetLimits(max_elapsed_seconds=0)


def test_defaults_always_apply(session):
    case = _case(session)
    assert case.limits["max_tool_operations"] == 50
    assert case.limits["max_elapsed_seconds"] == 600


def test_tool_operation_budget(session):
    case = _case(session, {"max_tool_operations": 2})
    budget = BudgetService(session, AuditService(session), case)
    budget.consume_tool_operation()
    budget.consume_tool_operation()
    assert not budget.can_run_tool()
    with pytest.raises(BudgetExceeded):
        budget.consume_tool_operation()


def test_evidence_budget(session):
    case = _case(session)
    budget = BudgetService(session, AuditService(session), case)
    with pytest.raises(BudgetExceeded):
        budget.consume_evidence(items=1, size_bytes=10_000_000)


def test_model_call_budget(session):
    case = _case(session, {"max_model_calls": 1})
    budget = BudgetService(session, AuditService(session), case)
    budget.consume_model_call()
    with pytest.raises(BudgetExceeded):
        budget.consume_model_call()


def test_retry_budget(session):
    case = _case(session)
    budget = BudgetService(session, AuditService(session), case)
    budget.consume_retry("op1")
    budget.consume_retry("op1")
    with pytest.raises(BudgetExceeded):
        budget.consume_retry("op1")


def test_budget_consumption_audited(session):
    case = _case(session)
    budget = BudgetService(session, AuditService(session), case)
    budget.consume_tool_operation()
    events = AuditService(session).list_events(case.id, event_type="budget_consumed")
    assert events
