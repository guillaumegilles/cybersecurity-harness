"""Feedback route (T054, FR-034)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from harness.api.app import get_analyst
from harness.api.identity import AnalystIdentity
from harness.analysis.feedback import record_feedback
from harness.audit.service import AuditService
from harness.storage.db import get_session
from harness.storage.repositories import CaseContext, CaseScopedRepository, get_case
from harness.storage.schemas import FeedbackRequest

router = APIRouter()


@router.post("/cases/{case_id}/feedback", status_code=201)
def post_feedback(case_id: str, req: FeedbackRequest,
                  analyst: AnalystIdentity = Depends(get_analyst)) -> dict:
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise HTTPException(status_code=403, detail="not authorized")
    if case.status in ("created", "running"):
        raise HTTPException(status_code=409, detail="investigation not finished")
    repo = CaseScopedRepository(
        session,
        CaseContext(case_id=case.id, analyst_id=analyst.analyst_id,
                    agent_execution_id=case.agent_execution_id),
    )
    fb = record_feedback(repo, AuditService(session), req)
    session.commit()
    return {"feedback_id": fb.id, "case_id": case.id, "rating": fb.rating}
