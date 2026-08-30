"""Report routes (T030)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from harness.api.app import get_analyst
from harness.api.identity import AnalystIdentity
from harness.report.generator import render_markdown
from harness.storage.db import get_session
from harness.storage.models import InvestigationReport
from harness.storage.repositories import get_case

router = APIRouter()


@router.get("/cases/{case_id}/report")
def get_report(case_id: str, format: str = "json",
               analyst: AnalystIdentity = Depends(get_analyst)):
    session = get_session()
    case = get_case(session, case_id, analyst.analyst_id)
    if case is None:
        raise HTTPException(status_code=403, detail="not authorized")
    report = session.scalars(
        select(InvestigationReport)
        .where(InvestigationReport.case_id == case.id)
        .order_by(InvestigationReport.generated_at.desc())
        .limit(1)
    ).first()
    if report is None:
        raise HTTPException(status_code=403, detail="not authorized")  # 403-safe (FR-019)
    if format == "markdown":
        return PlainTextResponse(render_markdown(report.content), media_type="text/markdown")
    return {"report_id": report.id, "report_kind": report.report_kind,
            "verified": report.verified, "content": report.content}
