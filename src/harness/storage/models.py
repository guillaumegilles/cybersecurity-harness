"""SQLAlchemy models for all data-model.md entities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class InvestigationCase(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    alert_id: Mapped[str] = mapped_column(String(256))
    alert_origin: Mapped[str] = mapped_column(String(32))  # connected_source | analyst_submitted
    analyst_id: Mapped[str] = mapped_column(String(128))
    agent_execution_id: Mapped[str] = mapped_column(String(36), default=_uuid)
    scope: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="created")
    workflow_state: Mapped[str] = mapped_column(String(48), default="RECEIVE_ALERT")
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    limits: Mapped[dict] = mapped_column(JSON, default=dict)
    spec_version: Mapped[str] = mapped_column(String(64), default="")
    app_version: Mapped[str] = mapped_column(String(32), default="")
    model_version: Mapped[str] = mapped_column(String(64), default="")
    policy_version: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CaseLink(Base):
    __tablename__ = "case_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id_a: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"))
    case_id_b: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"))
    linked_by: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    source: Mapped[str] = mapped_column(String(128))
    source_record_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trust_classification: Mapped[str] = mapped_column(String(32))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    transformation_history: Mapped[list] = mapped_column(JSON, default=list)
    manipulation_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_operation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(32))
    support_status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(16))
    material: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ClaimEvidenceLink(Base):
    __tablename__ = "claim_evidence_links"
    __table_args__ = (UniqueConstraint("claim_id", "evidence_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    claim_id: Mapped[str] = mapped_column(String(36), ForeignKey("claims.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_items.id"))
    relationship: Mapped[str] = mapped_column(String(16))  # supports|contradicts|inconclusive
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    evaluation: Mapped[str] = mapped_column(String(16))  # supported|rejected|inconclusive
    confirming_evidence_needed: Mapped[str] = mapped_column(Text, default="")
    rejecting_evidence_needed: Mapped[str] = mapped_column(Text, default="")
    claim_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AffectedEntity(Base):
    __tablename__ = "affected_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(24))
    identifier: Mapped[str] = mapped_column(String(256))
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class InvestigationReport(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    report_kind: Mapped[str] = mapped_column(String(16))  # complete|partial
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ResponseActionProposal(Base):
    __tablename__ = "response_action_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    action_description: Mapped[str] = mapped_column(Text)
    affected_resources: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    expected_impact: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    rollback_method: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ToolOperation(Base):
    __tablename__ = "tool_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    agent_execution_id: Mapped[str] = mapped_column(String(36))
    tool_name: Mapped[str] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(128))
    target_resource: Mapped[str] = mapped_column(String(256), default="")
    parameters_redacted: Mapped[dict] = mapped_column(JSON, default=dict)
    authorization_decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuthorizationDecision(Base):
    __tablename__ = "authorization_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    agent_identity: Mapped[str] = mapped_column(String(128))
    analyst_id: Mapped[str] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(128))
    target_resource: Mapped[str] = mapped_column(String(256), default="")
    budget_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(8))  # allow|deny
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class BudgetLedger(Base):
    __tablename__ = "budget_ledgers"

    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), primary_key=True)
    elapsed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    tool_operations_used: Mapped[int] = mapped_column(Integer, default=0)
    evidence_items: Mapped[int] = mapped_column(Integer, default=0)
    evidence_bytes: Mapped[int] = mapped_column(Integer, default=0)
    model_calls: Mapped[int] = mapped_column(Integer, default=0)
    cost_units: Mapped[int] = mapped_column(Integer, default=0)
    retries_by_operation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("case_id", "sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(48))
    actor: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalystFeedback(Base):
    __tablename__ = "analyst_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    analyst_id: Mapped[str] = mapped_column(String(128))
    rating: Mapped[str] = mapped_column(String(24))
    corrections: Mapped[str | None] = mapped_column(Text, nullable=True)
    irrelevant_evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    final_disposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
