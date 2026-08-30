"""Case lifecycle routes (T030, T059): create, get, cancel, link."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from harness.api.app import get_analyst
from harness.api.identity import AnalystIdentity
from harness.orchestrator import states
from harness.orchestrator.case_service import CaseCreationError, create_case, link_cases
from harness.storage.db import get_session
from harness.storage.repositories import get_case
from harness.storage.schemas import CaseLinkRequest, CreateCaseRequest, CreateCaseResponse

router = APIRouter()

# 403-safe not-found (FR-019): same response whether missing or unauthorized.
_NOT_ACCESSIBLE = HTTPException(status_code=403, detail="not authorized")


@router.post("/cases", status_code=201, response_model=CreateCaseResponse)
def post_case(
    req: CreateCaseRequest,
    background: BackgroundTasks,
    analyst: AnalystIdentity = Depends(get_analyst),
) -> CreateCaseResponse:
    session = get_session()
    try:
        case = create_case(session, analyst.analyst_id, req)
    except (CaseCreationError, ValueError) as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    session.commit()
    case_id = case.id
    limits = dict(case.limits)
    submitted = req.alert.content if req.alert.origin.value == "analyst_submitted" else None

    # Run synchronously in dev/eval (deterministic, fast with synthetic sources).
    fresh = get_session()
    fresh_case = fresh.get(type(case), case_id)
    states.run_investigation(fresh, fresh_case, analyst.authorized_sources, submitted)

    return CreateCaseResponse(
        case_id=case_id,
        status=fresh_case.status,
        workflow_state=fresh_case.workflow_state,
        limits={k: v for k, v in limits.items() if isinstance(v, int)},
    )


@router.get("/cases/{case_id}")
def get_case_summary(case_id: str, analyst: AnalystIdentity = Depends(get_analyst)) -> dict:
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise _NOT_ACCESSIBLE
    return {
        "case_id": case.id,
        "alert_id": case.alert_id,
        "status": case.status,
        "workflow_state": case.workflow_state,
        "termination_reason": case.termination_reason,
        "started_at": case.started_at.isoformat(),
        "completed_at": case.completed_at.isoformat() if case.completed_at else None,
        "limits": case.limits,
    }


@router.post("/cases/{case_id}/cancel", status_code=202)
def cancel_case(case_id: str, analyst: AnalystIdentity = Depends(get_analyst)) -> dict:
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise _NOT_ACCESSIBLE
    if case.status not in ("created", "running"):
        raise HTTPException(status_code=409, detail=f"case already terminal: {case.status}")
    states.request_cancel(case_id)
    return {"case_id": case_id, "status": "cancelling"}


@router.post("/cases/{case_id}/links", status_code=201)
def post_case_link(
    case_id: str, req: CaseLinkRequest, analyst: AnalystIdentity = Depends(get_analyst)
) -> dict:
    session = get_session()
    link = link_cases(session, analyst.analyst_id, case_id, req.other_case_id, req.reason)
    if link is None:
        raise _NOT_ACCESSIBLE
    session.commit()
    return {"link_id": link.id, "case_id_a": link.case_id_a, "case_id_b": link.case_id_b}
