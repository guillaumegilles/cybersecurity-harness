"""Concrete workflow execution (T028): wires case service, tool invoker,
evidence store, analysis, and report generation into the state machine.

Runs synchronously (dev/eval). Cancellation is cooperative: a flag checked
between states (T059, FR-005a).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from harness.analysis.claims import generate_hypotheses, generate_observation_claims
from harness.analysis.entities import extract_entities
from harness.analysis.proposals import generate_proposals
from harness.analysis.timeline import build_timeline
from harness.audit.service import AuditService
from harness.evidence.store import EvidenceStore
from harness.model.gateway import get_model_gateway
from harness.orchestrator.budget import BudgetExceeded, BudgetService
from harness.orchestrator.machine import (
    TERMINAL_STATUS,
    State,
    StateMachine,
)
from harness.policy.engine import PolicyEngine
from harness.report.generator import persist_report
from harness.report.verifier import verify_report
from harness.storage.models import AffectedEntity, InvestigationCase
from harness.storage.repositories import CaseContext, CaseScopedRepository
from harness.tools.invoker import ToolInvoker

# Cooperative cancellation registry (dev/eval; keyed by case_id).
_CANCEL_REQUESTS: set[str] = set()


def request_cancel(case_id: str) -> None:
    _CANCEL_REQUESTS.add(case_id)


def _cancelled(case_id: str) -> bool:
    return case_id in _CANCEL_REQUESTS


def run_investigation(
    session: Session,
    case: InvestigationCase,
    analyst_sources: tuple[str, ...],
    submitted_content: dict | None = None,
) -> InvestigationCase:
    audit = AuditService(session)
    ctx = CaseContext(case_id=case.id, analyst_id=case.analyst_id,
                      agent_execution_id=case.agent_execution_id)
    repo = CaseScopedRepository(session, ctx)
    budget = BudgetService(session, audit, case)
    policy = PolicyEngine(session, audit)

    machine = StateMachine(
        on_transition=lambda prev, new: _on_transition(audit, case, prev, new),
    )
    invoker = ToolInvoker(
        repo, policy, budget, audit, analyst_sources,
        permitted_tools_fn=machine.permitted_tools,
    )
    store = EvidenceStore(repo, audit, budget)
    case.status = "running"
    limitations: list[str] = []

    def _check_cancel() -> bool:
        if _cancelled(case.id):
            machine.cancel_requested = True
            return True
        return False

    try:
        # RECEIVE_ALERT -> VALIDATE_REQUEST
        machine.advance()
        if machine.current == State.CANCELLED:
            return _finalize(session, case, repo, audit, machine.current, "cancelled by analyst", limitations)

        # VALIDATE_REQUEST: intake validated at case creation.
        machine.advance()  # -> AUTHORIZE

        # AUTHORIZE: identity/claims were verified at API layer; deny if no sources at all.
        if not analyst_sources:
            machine.transition_to(State.ACCESS_DENIED)
            return _finalize(session, case, repo, audit, machine.current,
                             "analyst has no authorized data sources", limitations)
        machine.advance()  # -> CLASSIFY_ALERT
        if _check_cancel():
            machine.advance()
            return _finalize(session, case, repo, audit, machine.current, "cancelled by analyst", limitations)

        # CLASSIFY_ALERT: retrieve alert detail (connected) or use submitted content.
        if case.alert_origin == "connected_source":
            result = invoker.invoke("alert_source.get_alert", {"alert_id": case.alert_id})
            if result.outcome == "denied":
                machine.transition_to(State.ACCESS_DENIED)
                return _finalize(session, case, repo, audit, machine.current,
                                 f"alert retrieval denied: {result.reason}", limitations)
            if not result.ok:
                machine.transition_to(State.SOURCE_UNAVAILABLE)
                limitations.append("Alert source unavailable; alert details not retrieved")
                return _finalize(session, case, repo, audit, machine.current,
                                 f"alert source failure: {result.reason}", limitations)
            store.add("alert_source", result.data, "direct_observation",
                      source_record_id=case.alert_id,
                      event_at=result.data.get("detected_at"),
                      tool_operation_id=result.operation_id)
        else:
            # Analyst-submitted content: untrusted, analyst-provided (FR-001).
            store.add("analyst_submission", submitted_content or {"alert_id": case.alert_id},
                      "analyst_provided", source_record_id=case.alert_id)
        machine.advance()  # -> CREATE_INVESTIGATION_PLAN
        machine.advance()  # -> COLLECT_EVIDENCE
        if _check_cancel():
            machine.advance()
            return _finalize(session, case, repo, audit, machine.current, "cancelled by analyst", limitations)

        # COLLECT_EVIDENCE
        _collect_evidence(case, invoker, store, limitations)
        machine.advance()  # -> NORMALIZE_EVIDENCE
        if _check_cancel():
            machine.advance()
            return _finalize(session, case, repo, audit, machine.current, "cancelled by analyst", limitations)

        # NORMALIZE_EVIDENCE: timeline + entities (deterministic).
        build_timeline(repo)
        extract_entities(repo)
        generate_observation_claims(repo, audit)

        # Identity/asset enrichment for discovered entities.
        _enrich_entities(repo, invoker, store, limitations)

        machine.advance()  # -> FORM_HYPOTHESES
        if _check_cancel():
            machine.advance()
            return _finalize(session, case, repo, audit, machine.current, "cancelled by analyst", limitations)

        # FORM_HYPOTHESES (model-assisted; model output untrusted).
        model = get_model_gateway()
        generate_hypotheses(repo, audit, budget, model,
                            objective=f"Investigate alert {case.alert_id} within case scope")
        machine.advance()  # -> VALIDATE_HYPOTHESES

        # VALIDATE_HYPOTHESES: proposals derived from supported hypotheses only.
        generate_proposals(repo)
        machine.advance()  # -> PRODUCE_REPORT

        # PRODUCE_REPORT + VERIFY_OUTPUT
        from harness.report.generator import build_report_content
        content = build_report_content(case, repo, limitations)
        problems = verify_report(content.model_dump(mode="json"), repo)
        machine.advance()  # -> VERIFY_OUTPUT
        if problems:
            audit.append(case.id, "security_event", actor="output_verifier",
                         payload={"problems": problems})
            machine.transition_to(State.VALIDATION_FAILED)
            return _finalize(session, case, repo, audit, machine.current,
                             f"output verification failed: {problems}", limitations)

        machine.advance()  # -> COMPLETE
        case.status = TERMINAL_STATUS[State.COMPLETE]
        case.completed_at = datetime.now(timezone.utc)
        case.workflow_state = machine.current.value
        persist_report(case, repo, audit, report_kind="complete",
                       limitations=limitations, verified=True)
        session.commit()
        return case

    except BudgetExceeded as exc:
        try:
            machine.transition_to(State.BUDGET_EXCEEDED)
        except Exception:
            pass
        return _finalize(session, case, repo, audit, State.BUDGET_EXCEEDED,
                         f"budget exhausted: {exc.limit_name} ({exc.detail})", limitations)
    except Exception as exc:  # fail safely (FR-033); never expand authorization
        try:
            if machine.current not in TERMINAL_STATUS:
                machine.fail()
        except Exception:
            pass
        terminal = machine.current if machine.current in TERMINAL_STATUS else State.SYSTEM_ERROR
        return _finalize(session, case, repo, audit, terminal,
                         f"system error: {type(exc).__name__}", limitations)
    finally:
        _CANCEL_REQUESTS.discard(case.id)


def _collect_evidence(case, invoker: ToolInvoker, store: EvidenceStore,
                      limitations: list[str]) -> None:
    res = invoker.invoke("alert_source.get_related_events", {"alert_id": case.alert_id})
    if res.ok and res.data:
        for ev in res.data.get("events", []):
            store.add("alert_source", ev, "direct_observation",
                      source_record_id=ev.get("event_id"), event_at=ev.get("event_at"),
                      tool_operation_id=res.operation_id)
    elif res.outcome != "denied":
        limitations.append("Related events could not be retrieved from alert source")


def _enrich_entities(repo: CaseScopedRepository, invoker: ToolInvoker,
                     store: EvidenceStore, limitations: list[str]) -> None:
    for ent in list(repo.list(AffectedEntity)):
        if ent.entity_type == "endpoint":
            res = invoker.invoke("endpoint_telemetry.get_events", {"endpoint_id": ent.identifier})
            if res.ok and res.data:
                for ev in res.data.get("events", []):
                    store.add("endpoint_telemetry", ev, "direct_observation",
                              source_record_id=ev.get("event_id"), event_at=ev.get("event_at"),
                              tool_operation_id=res.operation_id)
            elif res.outcome == "denied":
                pass  # denial is authoritative; no substitution (FR-024)
            else:
                limitations.append(f"Endpoint telemetry unavailable for {ent.identifier}")
            res2 = invoker.invoke("identity_context.get_asset", {"asset_id": ent.identifier})
            if res2.ok and res2.data:
                store.add("identity_context", res2.data, "direct_observation",
                          source_record_id=ent.identifier, tool_operation_id=res2.operation_id)
        elif ent.entity_type == "user":
            res = invoker.invoke("identity_context.get_user", {"user_id": ent.identifier})
            if res.ok and res.data:
                store.add("identity_context", res.data, "direct_observation",
                          source_record_id=ent.identifier, tool_operation_id=res.operation_id)


def _on_transition(audit: AuditService, case, prev: State, new: State) -> None:
    case.workflow_state = new.value
    audit.append(case.id, "state_transition", actor="orchestrator",
                 payload={"from": prev.value, "to": new.value})


def _finalize(session: Session, case, repo, audit: AuditService, terminal: State,
              reason: str, limitations: list[str]):
    """Safe termination: partial report + exact reason (T058, FR-032)."""
    case.status = TERMINAL_STATUS.get(terminal, "failed_safely")
    case.termination_reason = reason
    case.completed_at = datetime.now(timezone.utc)
    case.workflow_state = terminal.value
    lims = limitations + [f"Investigation terminated early: {reason}"]
    try:
        persist_report(case, repo, audit, report_kind="partial",
                       limitations=lims, verified=False)
    except Exception:
        pass  # report generation must never mask the terminal status
    session.commit()
    return case
