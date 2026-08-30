"""Malformed-input / replay / memory-poisoning adversarial tests (T064, FR-033).

Covers Constitution VI categories: malicious/malformed tool responses,
oversized evidence, repeated/replayed operations, memory poisoning, and
endless-execution prevention.
"""

from __future__ import annotations

import pytest

from harness.audit.service import AuditService
from harness.model.gateway import FakeModel
from harness.orchestrator.budget import BudgetExceeded, BudgetService
from harness.orchestrator.case_service import create_case
from harness.policy.engine import PolicyEngine
from harness.storage.repositories import CaseContext, CaseScopedRepository
from harness.storage.schemas import AlertInput, AlertOrigin, CreateCaseRequest
from harness.tools.invoker import ToolInvoker

ALL = ("alert_source", "endpoint_telemetry", "identity_context")


@pytest.fixture()
def rig(session):
    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "alice", case.agent_execution_id))
    invoker = ToolInvoker(repo, PolicyEngine(session, audit),
                          BudgetService(session, audit, case), audit, ALL)
    return case, invoker, audit, session


def test_malformed_tool_response_rejected(rig, monkeypatch):
    case, invoker, audit, _ = rig
    from harness.tools import registry
    tool = registry.TOOL_REGISTRY["alert_source.get_alert"]
    monkeypatch.setattr(tool, "handler", lambda **kw: "not-a-dict", raising=False) if False else None
    # RegisteredTool is frozen; patch via a wrapper registry entry instead.
    import dataclasses
    bad = dataclasses.replace(tool, handler=lambda **kw: "not-a-dict")
    monkeypatch.setitem(registry.TOOL_REGISTRY, "alert_source.get_alert", bad)
    result = invoker.invoke("alert_source.get_alert", {"alert_id": "ALERT-1001"})
    assert result.outcome == "malformed_result"
    assert result.data is None
    failures = audit.list_events(case.id, event_type="tool_failure")
    assert failures


def test_oversized_result_refused(rig, monkeypatch):
    case, invoker, audit, _ = rig
    from harness.tools import registry
    import dataclasses
    tool = registry.TOOL_REGISTRY["alert_source.get_alert"]
    big = dataclasses.replace(tool, handler=lambda **kw: {"blob": "x" * 2_000_000})
    monkeypatch.setitem(registry.TOOL_REGISTRY, "alert_source.get_alert", big)
    result = invoker.invoke("alert_source.get_alert", {"alert_id": "ALERT-1001"})
    assert result.outcome == "oversized_result"
    assert result.data is None


def test_replayed_operations_bounded_by_budget(rig):
    """Replaying the same operation cannot run endlessly: tool budget stops it."""
    case, invoker, _, _ = rig
    with pytest.raises(BudgetExceeded):
        for _ in range(1000):
            invoker.invoke("alert_source.get_alert", {"alert_id": "ALERT-1001"})


def test_retry_budget_prevents_endless_retries(session):
    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    budget = BudgetService(session, AuditService(session), case)
    budget.consume_retry("flaky_op")
    budget.consume_retry("flaky_op")
    with pytest.raises(BudgetExceeded):
        budget.consume_retry("flaky_op")


def test_memory_poisoning_no_durable_instruction_store():
    """FR-005/FR-026: no durable cross-case memory exists to poison."""
    import harness.storage.models as m
    tables = {t.name for t in m.Base.metadata.tables.values()}
    for forbidden in ("agent_memory", "memories", "instructions", "persistent_context"):
        assert forbidden not in tables
    # Model gateway is stateless: no memory attribute or store.
    fm = FakeModel()
    assert not hasattr(fm, "memory")
    assert not hasattr(fm, "history")


def test_hostile_model_output_degrades_to_inconclusive(session):
    """Malicious model output (invalid enums / garbage) cannot poison claims."""
    from harness.analysis.claims import generate_hypotheses
    from harness.evidence.store import EvidenceStore

    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "alice", case.agent_execution_id))
    budget = BudgetService(session, audit, case)

    class EvilModel:
        model_version = "evil"

        def complete(self, system, user):
            return ('{"hypotheses": [{"statement": "attacker confirmed, execute isolation", '
                    '"evaluation": "ABSOLUTELY_CERTAIN", "confidence": "1000%"}]}')

    hyps = generate_hypotheses(repo, audit, budget, EvilModel(), "objective")
    assert all(h.evaluation in ("supported", "rejected", "inconclusive") for h in hyps)
    # Invalid enum degraded to inconclusive; never presented as supported fact.
    assert hyps[0].evaluation == "inconclusive"


def test_garbage_model_output_handled(session):
    from harness.analysis.claims import generate_hypotheses

    case = create_case(
        session, "alice",
        CreateCaseRequest(alert=AlertInput(origin=AlertOrigin.connected_source, alert_id="ALERT-1001")),
    )
    audit = AuditService(session)
    repo = CaseScopedRepository(session, CaseContext(case.id, "alice", case.agent_execution_id))
    budget = BudgetService(session, audit, case)

    class GarbageModel:
        model_version = "garbage"

        def complete(self, system, user):
            return "<<<not json at all>>>"

    hyps = generate_hypotheses(repo, audit, budget, GarbageModel(), "objective")
    assert len(hyps) == 1
    assert hyps[0].evaluation == "inconclusive"
