"""Deterministic state machine (T013, Constitution V).

Explicit workflow + terminal states, transition table, per-state config.
No runtime-created states, tools, or execution paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class State(str, Enum):
    # Workflow states (Constitution V)
    RECEIVE_ALERT = "RECEIVE_ALERT"
    VALIDATE_REQUEST = "VALIDATE_REQUEST"
    AUTHORIZE = "AUTHORIZE"
    CLASSIFY_ALERT = "CLASSIFY_ALERT"
    CREATE_INVESTIGATION_PLAN = "CREATE_INVESTIGATION_PLAN"
    COLLECT_EVIDENCE = "COLLECT_EVIDENCE"
    NORMALIZE_EVIDENCE = "NORMALIZE_EVIDENCE"
    FORM_HYPOTHESES = "FORM_HYPOTHESES"
    VALIDATE_HYPOTHESES = "VALIDATE_HYPOTHESES"
    PRODUCE_REPORT = "PRODUCE_REPORT"
    VERIFY_OUTPUT = "VERIFY_OUTPUT"
    COMPLETE = "COMPLETE"
    # Terminal states
    ACCESS_DENIED = "ACCESS_DENIED"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    CANCELLED = "CANCELLED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


TERMINAL_STATES = frozenset(
    {
        State.COMPLETE,
        State.ACCESS_DENIED,
        State.INCOMPLETE_EVIDENCE,
        State.SOURCE_UNAVAILABLE,
        State.POLICY_BLOCKED,
        State.BUDGET_EXCEEDED,
        State.VALIDATION_FAILED,
        State.CANCELLED,
        State.SYSTEM_ERROR,
    }
)

# Terminal state -> case status (data-model.md mapping)
TERMINAL_STATUS: dict[State, str] = {
    State.COMPLETE: "completed",
    State.BUDGET_EXCEEDED: "budget_exhausted",
    State.CANCELLED: "cancelled",
    State.ACCESS_DENIED: "denied",
    State.POLICY_BLOCKED: "denied",
    State.INCOMPLETE_EVIDENCE: "partially_completed",
    State.SOURCE_UNAVAILABLE: "partially_completed",
    State.VALIDATION_FAILED: "failed_safely",
    State.SYSTEM_ERROR: "failed_safely",
}

# Normal path transition table.
NEXT_STATE: dict[State, State] = {
    State.RECEIVE_ALERT: State.VALIDATE_REQUEST,
    State.VALIDATE_REQUEST: State.AUTHORIZE,
    State.AUTHORIZE: State.CLASSIFY_ALERT,
    State.CLASSIFY_ALERT: State.CREATE_INVESTIGATION_PLAN,
    State.CREATE_INVESTIGATION_PLAN: State.COLLECT_EVIDENCE,
    State.COLLECT_EVIDENCE: State.NORMALIZE_EVIDENCE,
    State.NORMALIZE_EVIDENCE: State.FORM_HYPOTHESES,
    State.FORM_HYPOTHESES: State.VALIDATE_HYPOTHESES,
    State.VALIDATE_HYPOTHESES: State.PRODUCE_REPORT,
    State.PRODUCE_REPORT: State.VERIFY_OUTPUT,
    State.VERIFY_OUTPUT: State.COMPLETE,
}


@dataclass(frozen=True)
class StateConfig:
    """Per-state config (Constitution V)."""

    permitted_tools: frozenset[str] = frozenset()
    max_retries: int = 2
    timeout_seconds: int = 120
    failure_transition: State = State.SYSTEM_ERROR


STATE_CONFIG: dict[State, StateConfig] = {
    State.RECEIVE_ALERT: StateConfig(failure_transition=State.VALIDATION_FAILED),
    State.VALIDATE_REQUEST: StateConfig(failure_transition=State.VALIDATION_FAILED),
    State.AUTHORIZE: StateConfig(failure_transition=State.ACCESS_DENIED),
    State.CLASSIFY_ALERT: StateConfig(
        permitted_tools=frozenset({"alert_source.get_alert"}),
        failure_transition=State.SOURCE_UNAVAILABLE,
    ),
    State.CREATE_INVESTIGATION_PLAN: StateConfig(),
    State.COLLECT_EVIDENCE: StateConfig(
        permitted_tools=frozenset(
            {
                "alert_source.get_related_events",
                "endpoint_telemetry.get_events",
                "identity_context.get_user",
                "identity_context.get_asset",
            }
        ),
        failure_transition=State.INCOMPLETE_EVIDENCE,
        timeout_seconds=300,
    ),
    State.NORMALIZE_EVIDENCE: StateConfig(
        permitted_tools=frozenset(
            {
                "endpoint_telemetry.get_events",
                "identity_context.get_user",
                "identity_context.get_asset",
            }
        ),
        failure_transition=State.VALIDATION_FAILED,
    ),
    State.FORM_HYPOTHESES: StateConfig(),
    State.VALIDATE_HYPOTHESES: StateConfig(),
    State.PRODUCE_REPORT: StateConfig(failure_transition=State.VALIDATION_FAILED),
    State.VERIFY_OUTPUT: StateConfig(failure_transition=State.VALIDATION_FAILED),
}


class InvalidTransition(Exception):
    pass


class CancellationRequested(Exception):
    """Raised cooperatively between states when the analyst cancels (FR-005a)."""


@dataclass
class StateMachine:
    """Drives a case through the workflow; records every transition via callback."""

    on_transition: Callable[[State, State], None]
    current: State = State.RECEIVE_ALERT
    cancel_requested: bool = False
    history: list[State] = field(default_factory=list)

    def advance(self) -> State:
        if self.current in TERMINAL_STATES:
            raise InvalidTransition(f"{self.current} is terminal")
        if self.cancel_requested:
            return self.transition_to(State.CANCELLED)
        nxt = NEXT_STATE[self.current]
        return self.transition_to(nxt)

    def fail(self) -> State:
        cfg = STATE_CONFIG.get(self.current)
        target = cfg.failure_transition if cfg else State.SYSTEM_ERROR
        return self.transition_to(target)

    def transition_to(self, target: State) -> State:
        if self.current in TERMINAL_STATES:
            raise InvalidTransition(f"cannot leave terminal state {self.current}")
        valid = target == NEXT_STATE.get(self.current) or target in TERMINAL_STATES
        if not valid:
            raise InvalidTransition(f"{self.current} -> {target} not permitted")
        prev = self.current
        self.current = target
        self.history.append(target)
        self.on_transition(prev, target)
        return target

    def permitted_tools(self) -> frozenset[str]:
        cfg = STATE_CONFIG.get(self.current)
        return cfg.permitted_tools if cfg else frozenset()
