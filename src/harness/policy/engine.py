"""Policy Engine — the single Policy Enforcement Point (T011).

Deny-by-default authorization of every tool operation, outside the model
(Constitution III). Absence or ambiguity of any input results in denial.
Denial reasons never reveal whether inaccessible data exists (FR-019).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from harness.audit.service import AuditService
from harness.policy import rules
from harness.storage.models import AuthorizationDecision


@dataclass(frozen=True)
class AuthorizationRequest:
    agent_identity: str
    analyst_id: str
    analyst_sources: tuple[str, ...]
    case_id: str
    operation: str
    tool_name: str
    target_source: str
    target_resource: str
    registered_operations: frozenset[str]
    budget_ok: bool
    budget_snapshot: dict


class PolicyEngine:
    """Deterministic PEP. The model never participates in these decisions."""

    def __init__(self, session: Session, audit: AuditService) -> None:
        self._session = session
        self._audit = audit

    def authorize(self, req: AuthorizationRequest) -> AuthorizationDecision:
        decision, reason = self._evaluate(req)
        record = AuthorizationDecision(
            case_id=req.case_id,
            agent_identity=req.agent_identity,
            analyst_id=req.analyst_id,
            operation=req.operation,
            target_resource=req.target_resource,
            budget_snapshot=req.budget_snapshot,
            decision=decision,
            reason=reason,
        )
        self._session.add(record)
        self._session.flush()

        self._audit.append(
            req.case_id,
            "authorization_decision",
            actor=req.agent_identity,
            payload={
                "operation": req.operation,
                "target_resource": req.target_resource,
                "decision": decision,
                "reason": reason,
                "decision_id": record.id,
            },
        )
        if decision == "deny":
            self._audit.append(
                req.case_id,
                "policy_denial",
                actor="policy_engine",
                payload={"operation": req.operation, "reason": reason},
            )
        return record

    def _evaluate(self, req: AuthorizationRequest) -> tuple[str, str]:
        # 0. Ambiguity/absence -> deny (Constitution III).
        if not req.agent_identity or not req.analyst_id or not req.case_id or not req.operation:
            return "deny", rules.DENY_REASON_AMBIGUOUS
        # 1. Prohibited operation classes (FR-017).
        if rules.is_prohibited(req.operation) or rules.is_prohibited(req.tool_name):
            return "deny", rules.DENY_REASON_PROHIBITED
        # 2. Only registered operations (FR-021); default deny.
        if req.operation not in req.registered_operations:
            return "deny", rules.DENY_REASON_UNREGISTERED
        # 3. Analyst source authorization (FR-019: opaque denial).
        if req.target_source not in req.analyst_sources:
            return "deny", rules.DENY_REASON_UNAUTHORIZED_SOURCE
        # 4. Budget (FR-022).
        if not req.budget_ok:
            return "deny", rules.DENY_REASON_BUDGET
        return "allow", "authorized"
