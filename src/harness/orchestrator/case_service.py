"""Case lifecycle service (T024, FR-001/FR-002)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from harness.audit.service import AuditService
from harness.config.settings import BudgetLimits, get_settings
from harness.storage.models import CaseLink, InvestigationCase
from harness.storage.repositories import get_case
from harness.storage.schemas import AlertOrigin, CreateCaseRequest


class CaseCreationError(Exception):
    pass


def create_case(session: Session, analyst_id: str, req: CreateCaseRequest) -> InvestigationCase:
    settings = get_settings()

    if req.alert.origin == AlertOrigin.connected_source:
        if not req.alert.alert_id:
            raise CaseCreationError("alert_id required for connected_source origin")
        alert_id = req.alert.alert_id
    else:
        if not req.alert.content:
            raise CaseCreationError("content required for analyst_submitted origin")
        alert_id = req.alert.alert_id or f"ANALYST-{uuid.uuid4().hex[:8].upper()}"

    # Validate limit overrides against hard bounds (FR-031); raises on invalid.
    limits = BudgetLimits(**{**settings.default_limits.model_dump(), **(req.limit_overrides or {})})

    case = InvestigationCase(
        alert_id=alert_id,
        alert_origin=req.alert.origin.value,
        analyst_id=analyst_id,
        agent_execution_id=str(uuid.uuid4()),
        scope=f"Investigate single alert {alert_id}; approved read-only sources only",
        limits=limits.model_dump(),
        spec_version=settings.spec_version,
        app_version=settings.app_version,
        model_version=settings.model_name,
        policy_version=settings.policy_version,
    )
    session.add(case)
    session.flush()

    audit = AuditService(session)
    audit.append(case.id, "case_created", actor=analyst_id,
                 payload={"alert_id": alert_id, "origin": case.alert_origin,
                          "agent_execution_id": case.agent_execution_id,
                          "limits": case.limits})
    audit.append(case.id, "scope_set", actor="system", payload={"scope": case.scope})
    return case


def link_cases(session: Session, analyst_id: str, case_id: str, other_case_id: str,
               reason: str) -> CaseLink | None:
    """Explicit case linking (FR-003). Analyst must access BOTH cases."""
    a = get_case(session, case_id, analyst_id)
    b = get_case(session, other_case_id, analyst_id)
    if a is None or b is None:
        return None
    link = CaseLink(case_id_a=a.id, case_id_b=b.id, linked_by=analyst_id, reason=reason)
    session.add(link)
    session.flush()
    audit = AuditService(session)
    audit.append(a.id, "case_linked", actor=analyst_id,
                 payload={"other_case_id": b.id, "reason": reason})
    audit.append(b.id, "case_linked", actor=analyst_id,
                 payload={"other_case_id": a.id, "reason": reason})
    return link
