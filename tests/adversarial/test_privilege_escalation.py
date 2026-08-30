"""Privilege escalation adversarial tests (T037, Constitution VI)."""

from __future__ import annotations

import pytest

from harness.audit.service import AuditService
from harness.orchestrator.budget import BudgetService
from harness.orchestrator.case_service import create_case
from harness.policy.engine import PolicyEngine
from harness.storage.repositories import CaseContext, CaseScopedRepository
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest
from harness.tools.invoker import ToolInvoker
from harness.tools.registry import TOOL_REGISTRY


@pytest.fixture()
def invoker(session):
    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "alice", case.agent_execution_id))
    return ToolInvoker(repo, PolicyEngine(session, audit),
                       BudgetService(session, audit, case), audit,
                       ("alert_source",)), case, audit


def test_probing_after_denial_still_denied(invoker):
    """Constitution III: denial is authoritative; probing finds no privileges."""
    inv, case, _ = invoker
    probes = ["endpoint_telemetry.get_events", "identity_context.get_user",
              "identity_context.get_asset", "admin.get_all", "debug.bypass"]
    for op in probes:
        params = {"endpoint_id": "WS-042"} if "endpoint" in op else {"user_id": "j.doe"} \
            if "user" in op else {"asset_id": "WS-042"} if "asset" in op else {}
        result = inv.invoke(op, params)
        assert result.outcome == "denied"


def test_tool_argument_manipulation_rejected(invoker):
    """Malicious/malformed arguments never reach the connector."""
    inv, _, _ = invoker
    result = inv.invoke("alert_source.get_related_events",
                        {"alert_id": "ALERT-1001", "max_results": 999999})
    assert result.outcome == "failed"
    assert "invalid input" in result.reason


def test_registry_is_static():
    """No runtime tool registration path exists (FR-021)."""
    assert isinstance(TOOL_REGISTRY, dict)
    import harness.tools.registry as reg
    assert not hasattr(reg, "register_tool")
    assert not hasattr(reg, "add_tool")


def test_unregistered_tool_names_denied(invoker):
    inv, _, _ = invoker
    for name in ["shell_exec", "http.post", "python.eval",
                 "alert_source.get_alert; DROP TABLE cases", "alert_source.get_alert\x00admin"]:
        assert inv.invoke(name, {}).outcome == "denied"
