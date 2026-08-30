"""Reviewer audit routes (T044, FR-028–FR-030)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from harness.api.app import get_analyst
from harness.api.identity import AnalystIdentity
from harness.audit.service import AuditService
from harness.storage.db import get_session
from harness.storage.repositories import get_case

router = APIRouter()


@router.get("/cases/{case_id}/audit")
def get_audit(case_id: str, after_sequence: int = 0, event_type: str | None = None,
              analyst: AnalystIdentity = Depends(get_analyst)) -> dict:
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise HTTPException(status_code=403, detail="not authorized")
    events = AuditService(session).list_events(case.id, after_sequence, event_type)
    return {
        "case_id": case.id,
        "events": [
            {
                "sequence": e.sequence,
                "event_type": e.event_type,
                "actor": e.actor,
                "payload": e.payload,
                "prev_hash": e.prev_hash,
                "event_hash": e.event_hash,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/cases/{case_id}/audit/verify")
def verify_audit(case_id: str, analyst: AnalystIdentity = Depends(get_analyst)) -> dict:
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise HTTPException(status_code=403, detail="not authorized")
    return AuditService(session).verify_chain(case.id)
