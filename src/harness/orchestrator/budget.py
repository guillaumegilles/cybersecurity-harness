"""Budget enforcement (T012, FR-031/FR-032)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from harness.audit.service import AuditService
from harness.config.settings import BudgetLimits
from harness.storage.models import BudgetLedger, InvestigationCase


class BudgetExceeded(Exception):
    def __init__(self, limit_name: str, detail: str) -> None:
        self.limit_name = limit_name
        self.detail = detail
        super().__init__(f"budget exceeded: {limit_name} ({detail})")


class BudgetService:
    def __init__(self, session: Session, audit: AuditService, case: InvestigationCase) -> None:
        self._session = session
        self._audit = audit
        self._case = case
        self._limits = BudgetLimits(**case.limits)
        ledger = session.get(BudgetLedger, case.id)
        if ledger is None:
            ledger = BudgetLedger(case_id=case.id)
            session.add(ledger)
            session.flush()
        self._ledger = ledger

    @property
    def limits(self) -> BudgetLimits:
        return self._limits

    def snapshot(self) -> dict:
        led = self._ledger
        return {
            "elapsed_seconds": self._elapsed(),
            "tool_operations_used": led.tool_operations_used,
            "evidence_items": led.evidence_items,
            "evidence_bytes": led.evidence_bytes,
            "model_calls": led.model_calls,
        }

    def _elapsed(self) -> int:
        started = self._case.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - started).total_seconds())

    def _consume(self, kind: str, amount: int) -> None:
        self._audit.append(
            self._case.id,
            "budget_consumed",
            actor="orchestrator",
            payload={"kind": kind, "amount": amount, "snapshot": self.snapshot()},
        )

    def check_time(self) -> None:
        if self._elapsed() > self._limits.max_elapsed_seconds:
            raise BudgetExceeded("max_elapsed_seconds", f"elapsed={self._elapsed()}s")

    def can_run_tool(self) -> bool:
        return (
            self._ledger.tool_operations_used < self._limits.max_tool_operations
            and self._elapsed() <= self._limits.max_elapsed_seconds
        )

    def consume_tool_operation(self) -> None:
        if not self.can_run_tool():
            raise BudgetExceeded("max_tool_operations", str(self._ledger.tool_operations_used))
        self._ledger.tool_operations_used += 1
        self._consume("tool_operation", 1)

    def consume_evidence(self, items: int, size_bytes: int) -> None:
        if self._ledger.evidence_items + items > self._limits.max_evidence_items:
            raise BudgetExceeded("max_evidence_items", str(self._ledger.evidence_items + items))
        if self._ledger.evidence_bytes + size_bytes > self._limits.max_evidence_bytes:
            raise BudgetExceeded("max_evidence_bytes", str(self._ledger.evidence_bytes + size_bytes))
        self._ledger.evidence_items += items
        self._ledger.evidence_bytes += size_bytes
        self._consume("evidence", items)

    def consume_model_call(self) -> None:
        if self._ledger.model_calls >= self._limits.max_model_calls:
            raise BudgetExceeded("max_model_calls", str(self._ledger.model_calls))
        self._ledger.model_calls += 1
        self._consume("model_call", 1)

    def consume_retry(self, operation: str) -> None:
        retries = dict(self._ledger.retries_by_operation)
        used = retries.get(operation, 0)
        if used >= self._limits.max_retries_per_operation:
            raise BudgetExceeded("max_retries_per_operation", f"{operation}: {used}")
        retries[operation] = used + 1
        self._ledger.retries_by_operation = retries
        self._consume("retry", 1)
