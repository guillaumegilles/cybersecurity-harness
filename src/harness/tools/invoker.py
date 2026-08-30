"""Tool invoker (T015, FR-022–FR-024).

Every call: PolicyEngine check -> budget check -> connector execution with
size enforcement -> ToolOperation persistence + audit events. Denials are
authoritative; there is no fallback/probing path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from harness.audit.service import AuditService
from harness.config.logging import redact_mapping
from harness.connectors.alert_source import ConnectorError, SourceUnavailable
from harness.orchestrator.budget import BudgetService
from harness.policy.engine import AuthorizationRequest, PolicyEngine
from harness.storage.models import ToolOperation
from harness.storage.repositories import CaseScopedRepository
from harness.tools.registry import REGISTERED_OPERATIONS, get_tool


@dataclass
class ToolResult:
    ok: bool
    outcome: str  # success|denied|failed|malformed_result|timeout|oversized_result
    data: dict[str, Any] | None
    operation_id: str
    reason: str = ""


class ToolInvoker:
    def __init__(
        self,
        repo: CaseScopedRepository,
        policy: PolicyEngine,
        budget: BudgetService,
        audit: AuditService,
        analyst_sources: tuple[str, ...],
        permitted_tools_fn=None,
    ) -> None:
        self._repo = repo
        self._policy = policy
        self._budget = budget
        self._audit = audit
        self._analyst_sources = analyst_sources
        self._permitted_tools_fn = permitted_tools_fn or (lambda: REGISTERED_OPERATIONS)

    def invoke(self, tool_name: str, params: dict[str, Any], target_resource: str = "") -> ToolResult:
        ctx = self._repo.ctx
        self._audit.append(
            ctx.case_id,
            "tool_requested",
            actor=ctx.agent_execution_id,
            payload={"tool": tool_name, "params": redact_mapping(dict(params))},
        )

        tool = get_tool(tool_name)
        state_permitted = self._permitted_tools_fn()
        registered_ops = REGISTERED_OPERATIONS & frozenset(state_permitted)

        decision = self._policy.authorize(
            AuthorizationRequest(
                agent_identity=ctx.agent_execution_id,
                analyst_id=ctx.analyst_id,
                analyst_sources=self._analyst_sources,
                case_id=ctx.case_id,
                operation=tool_name,
                tool_name=tool_name,
                target_source=tool.source if tool else "",
                target_resource=target_resource,
                registered_operations=registered_ops,
                budget_ok=self._budget.can_run_tool(),
                budget_snapshot=self._budget.snapshot(),
            )
        )

        op = ToolOperation(
            case_id=ctx.case_id,
            agent_execution_id=ctx.agent_execution_id,
            tool_name=tool_name,
            operation=tool_name,
            target_resource=target_resource,
            parameters_redacted=redact_mapping(dict(params)),
            authorization_decision_id=decision.id,
            outcome="pending",
        )
        self._repo.add(op)
        self._repo.session.flush()

        if decision.decision != "allow":
            op.outcome = "denied"
            op.completed_at = datetime.now(timezone.utc)
            if decision.reason == "budget_exhausted":
                # Reaching a limit stops the investigation safely (FR-032).
                from harness.orchestrator.budget import BudgetExceeded

                raise BudgetExceeded("max_tool_operations", "tool budget exhausted")
            # policy_denial already audited by PolicyEngine
            return ToolResult(False, "denied", None, op.id, reason=decision.reason)

        assert tool is not None  # allow implies registered
        self._budget.consume_tool_operation()

        try:
            validated = tool.input_schema(**params)
        except ValidationError as exc:
            op.outcome = "failed"
            op.completed_at = datetime.now(timezone.utc)
            self._audit.append(ctx.case_id, "tool_failure", actor="tool_invoker",
                               payload={"tool": tool_name, "error": "invalid_input"})
            return ToolResult(False, "failed", None, op.id, reason=f"invalid input: {exc.error_count()} errors")

        try:
            data = tool.handler(**validated.model_dump())
        except SourceUnavailable:
            op.outcome = "failed"
            op.completed_at = datetime.now(timezone.utc)
            self._audit.append(ctx.case_id, "tool_failure", actor="tool_invoker",
                               payload={"tool": tool_name, "error": "unavailable"})
            return ToolResult(False, "failed", None, op.id, reason="source unavailable")
        except ConnectorError as exc:
            op.outcome = "failed"
            op.completed_at = datetime.now(timezone.utc)
            self._audit.append(ctx.case_id, "tool_failure", actor="tool_invoker",
                               payload={"tool": tool_name, "error": str(exc)})
            return ToolResult(False, "failed", None, op.id, reason=str(exc))

        if not isinstance(data, dict):
            op.outcome = "malformed_result"
            op.completed_at = datetime.now(timezone.utc)
            self._audit.append(ctx.case_id, "tool_failure", actor="tool_invoker",
                               payload={"tool": tool_name, "error": "malformed_result"})
            return ToolResult(False, "malformed_result", None, op.id, reason="non-dict result")

        size = len(json.dumps(data, default=str).encode())
        if size > tool.max_result_bytes:
            op.outcome = "oversized_result"
            op.completed_at = datetime.now(timezone.utc)
            self._audit.append(ctx.case_id, "tool_failure", actor="tool_invoker",
                               payload={"tool": tool_name, "error": "oversized_result", "size": size})
            return ToolResult(False, "oversized_result", None, op.id, reason="result exceeds size limit")

        op.outcome = "success"
        op.completed_at = datetime.now(timezone.utc)
        self._audit.append(ctx.case_id, "source_accessed", actor=ctx.agent_execution_id,
                           payload={"source": tool.source, "tool": tool_name})
        self._audit.append(ctx.case_id, "tool_result", actor="tool_invoker",
                           payload={"tool": tool_name, "size_bytes": size, "outcome": "success"})
        return ToolResult(True, "success", data, op.id)
