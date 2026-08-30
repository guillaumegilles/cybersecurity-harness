"""Pydantic domain schemas (T008)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from harness.config.settings import BudgetLimits  # re-export for convenience

__all__ = ["BudgetLimits"]


class AlertOrigin(str, Enum):
    connected_source = "connected_source"
    analyst_submitted = "analyst_submitted"


class CaseStatus(str, Enum):
    created = "created"
    running = "running"
    completed = "completed"
    partially_completed = "partially_completed"
    denied = "denied"
    failed_safely = "failed_safely"
    cancelled = "cancelled"
    budget_exhausted = "budget_exhausted"


class TrustClassification(str, Enum):
    direct_observation = "direct_observation"
    correlated = "correlated"
    analyst_provided = "analyst_provided"
    unverified_external = "unverified_external"


class ClaimType(str, Enum):
    direct_observation = "direct_observation"
    correlation = "correlation"
    inference = "inference"
    analyst_provided = "analyst_provided"
    unverified_external = "unverified_external"


class SupportStatus(str, Enum):
    supported = "supported"
    unsupported = "unsupported"
    inferred = "inferred"
    inconclusive = "inconclusive"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    inconclusive = "inconclusive"


class Rating(str, Enum):
    useful = "useful"
    partially_useful = "partially_useful"
    not_useful = "not_useful"


# --- API request/response schemas ---


class AlertInput(BaseModel):
    origin: AlertOrigin
    alert_id: str | None = None
    content: dict[str, Any] | None = None


class CreateCaseRequest(BaseModel):
    alert: AlertInput
    limit_overrides: dict[str, int] | None = None


class CreateCaseResponse(BaseModel):
    case_id: str
    status: CaseStatus
    workflow_state: str
    limits: dict[str, int]


class FeedbackRequest(BaseModel):
    rating: Rating
    corrections: str | None = None
    irrelevant_evidence_ids: list[str] = Field(default_factory=list)
    final_disposition: str | None = None


class CaseLinkRequest(BaseModel):
    other_case_id: str
    reason: str


# --- Report content schema: all FR-013 sections ---


class TimelineEntry(BaseModel):
    event_at: datetime | None
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class EntityEntry(BaseModel):
    entity_type: str
    identifier: str
    evidence_ids: list[str] = Field(default_factory=list)


class FindingEntry(BaseModel):
    claim_id: str
    statement: str
    claim_type: ClaimType
    support_status: SupportStatus
    confidence: Confidence
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)


class HypothesisEntry(BaseModel):
    statement: str
    evaluation: str
    confirming_evidence_needed: str
    rejecting_evidence_needed: str


class ProposalEntry(BaseModel):
    action_description: str
    affected_resources: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    expected_impact: str
    risk: str
    rollback_method: str
    proposal_only: bool = True


class ToolOperationEntry(BaseModel):
    tool_name: str
    operation: str
    outcome: str
    requested_at: datetime | None = None


class ReportContent(BaseModel):
    """Structured report — every FR-013 section is a required field."""

    case_id: str
    alert_id: str
    status: str
    alert_summary: str
    scope: str
    timeline: list[TimelineEntry]
    affected_entities: list[EntityEntry]
    findings: list[FindingEntry]
    hypotheses: list[HypothesisEntry]
    contradicting_or_inconclusive_evidence: list[str]
    missing_information: list[str]
    severity_assessment: str
    recommended_queries: list[str]
    response_action_proposals: list[ProposalEntry]
    limitations: list[str]
    data_sources_consulted: list[str]
    tool_operations: list[ToolOperationEntry]
    started_at: datetime | None
    completed_at: datetime | None
