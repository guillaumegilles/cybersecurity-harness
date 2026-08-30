"""Analyst feedback service (T053, FR-034)."""

from __future__ import annotations

from harness.audit.service import AuditService
from harness.storage.models import AnalystFeedback
from harness.storage.repositories import CaseScopedRepository
from harness.storage.schemas import FeedbackRequest


def record_feedback(
    repo: CaseScopedRepository, audit: AuditService, req: FeedbackRequest
) -> AnalystFeedback:
    fb = AnalystFeedback(
        case_id=repo.ctx.case_id,
        analyst_id=repo.ctx.analyst_id,
        rating=req.rating.value,
        corrections=req.corrections,
        irrelevant_evidence_ids=req.irrelevant_evidence_ids,
        final_disposition=req.final_disposition,
    )
    repo.add(fb)
    repo.session.flush()
    audit.append(
        repo.ctx.case_id,
        "feedback_recorded",
        actor=repo.ctx.analyst_id,
        payload={"rating": req.rating.value, "has_corrections": bool(req.corrections)},
    )
    return fb
