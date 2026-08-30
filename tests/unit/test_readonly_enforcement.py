"""Read-only enforcement via the tool invoker (T036 complement)."""

from __future__ import annotations

import pytest

from harness.audit.service import AuditService
from harness.orchestrator.budget import BudgetService
from harness.orchestrator.case_service import create_case
from harness.policy.engine import PolicyEngine
from harness.storage.repositories import CaseContext, CaseScopedRepository
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest
from harness.tools.invoker import ToolInvoker

ALL = ("alert_source", "endpoint_telemetry", "identity_context")


@pytest.fixture()
def setup(session):
    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "alice", case.agent_execution_id))
    invoker = ToolInvoker(repo, PolicyEngine(session, audit), BudgetService(session, audit, case),
                          audit, ALL)
    return case, invoker, audit


@pytest.mark.parametrize("op", [
    "isolate_endpoint", "disable_account", "block_ip", "execute_command",
    "run_shell", "upload_external", "modify_audit", "install_tool", "create_subagent",
])
def test_prohibited_tools_denied_no_state_change(setup, op):
    case, invoker, audit = setup
    result = invoker.invoke(op, {"target": "WS-042"})
    assert result.outcome == "denied"
    assert result.data is None
    # denial recorded (FR-018)
    denials = audit.list_events(case.id, event_type="policy_denial")
    assert denials


def test_unregistered_tool_denied(setup):
    case, invoker, _ = setup
    result = invoker.invoke("some.new.tool", {})
    assert result.outcome == "denied"


def test_unauthorized_source_denial_reveals_nothing(session):
    """FR-019 / spec scenario 7."""
    case = create_case(
        session, "bob",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "bob", case.agent_execution_id))
    invoker = ToolInvoker(repo, PolicyEngine(session, audit), BudgetService(session, audit, case),
                          audit, ("alert_source",))  # bob lacks endpoint_telemetry
    result = invoker.invoke("endpoint_telemetry.get_events", {"endpoint_id": "WS-042"})
    assert result.outcome == "denied"
    assert "WS-042" not in result.reason
    assert "exist" not in result.reason.lower()


def test_denied_operation_consumes_no_budget(setup):
    case, invoker, _ = setup
    before = invoker._budget.snapshot()["tool_operations_used"]
    invoker.invoke("isolate_endpoint", {})
    after = invoker._budget.snapshot()["tool_operations_used"]
    assert before == after
