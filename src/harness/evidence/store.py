"""Evidence store (T025, FR-006/FR-008).

Verbatim persistence with full provenance; runs the instruction detector on
all incoming content and emits manipulation_detected audit events (FR-027).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from harness.audit.service import AuditService
from harness.evidence.instruction_detector import detect_instructions
from harness.orchestrator.budget import BudgetService
from harness.storage.models import EvidenceItem
from harness.storage.repositories import CaseScopedRepository


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class EvidenceStore:
    def __init__(self, repo: CaseScopedRepository, audit: AuditService, budget: BudgetService) -> None:
        self._repo = repo
        self._audit = audit
        self._budget = budget

    def add(
        self,
        source: str,
        content: dict[str, Any],
        trust_classification: str,
        source_record_id: str | None = None,
        event_at: str | None = None,
        tool_operation_id: str | None = None,
        transformation_history: list[str] | None = None,
    ) -> EvidenceItem:
        size = len(json.dumps(content, default=str).encode())
        self._budget.consume_evidence(items=1, size_bytes=size)

        matched = detect_instructions(content)
        item = EvidenceItem(
            case_id=self._repo.ctx.case_id,
            source=source,
            source_record_id=source_record_id,
            event_at=_parse_ts(event_at),
            trust_classification=trust_classification,
            content=content,  # verbatim — evidence is never sanitized (research R6)
            size_bytes=size,
            transformation_history=transformation_history or [],
            manipulation_flag=bool(matched),
            tool_operation_id=tool_operation_id,
        )
        self._repo.add(item)
        self._repo.session.flush()

        self._audit.append(
            self._repo.ctx.case_id,
            "evidence_collected",
            actor=self._repo.ctx.agent_execution_id,
            payload={"evidence_id": item.id, "source": source,
                     "source_record_id": source_record_id, "size_bytes": size},
        )
        if matched:
            self._audit.append(
                self._repo.ctx.case_id,
                "manipulation_detected",
                actor="instruction_detector",
                payload={"evidence_id": item.id, "patterns": matched[:5]},
            )
        return item
