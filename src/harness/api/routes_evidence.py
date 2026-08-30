"""Evidence provenance route (T035, FR-012)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from harness.api.app import get_analyst
from harness.api.identity import AnalystIdentity
from harness.evidence.provenance import claim_evidence
from harness.storage.db import get_session
from harness.storage.repositories import CaseContext, CaseScopedRepository, get_case

router = APIRouter()


@router.get("/cases/{case_id}/claims/{claim_id}/evidence")
def get_claim_evidence(case_id: str, claim_id: str,
                       analyst: AnalystIdentity = Depends(get_analyst)) -> dict:
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise HTTPException(status_code=403, detail="not authorized")
    repo = CaseScopedRepository(
        session,
        CaseContext(case_id=case.id, analyst_id=analyst.analyst_id,
                    agent_execution_id=case.agent_execution_id),
    )
    result = claim_evidence(repo, claim_id)
    if result is None:
        raise HTTPException(status_code=403, detail="not authorized")  # 403-safe
    return result
