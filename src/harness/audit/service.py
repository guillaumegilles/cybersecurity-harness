"""Append-only audit service with SHA-256 hash chaining (T010, FR-028–FR-030).

The investigating agent has no mutation path: this service only appends.
The audit table has no update/delete API anywhere in the codebase.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _ts(dt: datetime) -> str:
    """Canonical UTC timestamp (SQLite drops tzinfo on round-trip)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from harness.config.logging import redact_mapping
from harness.storage.models import AuditEvent

# Complete event-type set (superset of FR-028 categories; see data-model.md).
EVENT_TYPES = frozenset(
    {
        "case_created",
        "scope_set",
        "state_transition",
        "source_accessed",
        "tool_requested",
        "authorization_decision",
        "tool_result",
        "tool_failure",
        "evidence_collected",
        "claim_generated",
        "policy_denial",
        "manipulation_detected",
        "budget_consumed",
        "report_generated",
        "feedback_recorded",
        "case_linked",
        "secret_redacted",
        "security_event",
    }
)


class AuditError(Exception):
    pass


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


class AuditService:
    """Append-only, ordered, hash-chained audit trail."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        case_id: str,
        event_type: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> AuditEvent:
        if event_type not in EVENT_TYPES:
            raise AuditError(f"unknown audit event type: {event_type}")
        safe_payload = redact_mapping(payload or {})

        last = self._session.scalars(
            select(AuditEvent)
            .where(AuditEvent.case_id == case_id)
            .order_by(AuditEvent.sequence.desc())
            .limit(1)
        ).first()
        sequence = (last.sequence + 1) if last else 1
        prev_hash = last.event_hash if last else ""

        occurred_at = datetime.now(timezone.utc)
        body = _canonical(
            {
                "case_id": case_id,
                "sequence": sequence,
                "event_type": event_type,
                "actor": actor,
                "payload": safe_payload,
                "occurred_at": _ts(occurred_at),
                "prev_hash": prev_hash,
            }
        )
        event_hash = hashlib.sha256(body.encode()).hexdigest()

        event = AuditEvent(
            case_id=case_id,
            sequence=sequence,
            event_type=event_type,
            actor=actor,
            payload=safe_payload,
            prev_hash=prev_hash,
            event_hash=event_hash,
            occurred_at=occurred_at,
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_events(
        self, case_id: str, after_sequence: int = 0, event_type: str | None = None
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.case_id == case_id, AuditEvent.sequence > after_sequence)
            .order_by(AuditEvent.sequence)
        )
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        return list(self._session.scalars(stmt).all())

    def verify_chain(self, case_id: str) -> dict[str, Any]:
        events = self.list_events(case_id)
        prev_hash = ""
        for ev in events:
            body = _canonical(
                {
                    "case_id": ev.case_id,
                    "sequence": ev.sequence,
                    "event_type": ev.event_type,
                    "actor": ev.actor,
                    "payload": ev.payload,
                    "occurred_at": _ts(ev.occurred_at),
                    "prev_hash": prev_hash,
                }
            )
            expected = hashlib.sha256(body.encode()).hexdigest()
            if ev.prev_hash != prev_hash or ev.event_hash != expected:
                return {
                    "intact": False,
                    "events_checked": len(events),
                    "first_broken_sequence": ev.sequence,
                }
            prev_hash = ev.event_hash
        return {"intact": True, "events_checked": len(events), "first_broken_sequence": None}
