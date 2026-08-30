"""State machine tests (T020, Constitution V)."""

from __future__ import annotations

import pytest

from harness.orchestrator.machine import (
    NEXT_STATE,
    TERMINAL_STATES,
    TERMINAL_STATUS,
    InvalidTransition,
    State,
    StateMachine,
)


def _machine():
    transitions = []
    m = StateMachine(on_transition=lambda p, n: transitions.append((p, n)))
    return m, transitions


def test_normal_path_reaches_complete():
    m, transitions = _machine()
    while m.current != State.COMPLETE:
        m.advance()
    assert m.current == State.COMPLETE
    assert len(transitions) == 11


def test_terminal_states_are_final():
    m, _ = _machine()
    m.transition_to(State.CANCELLED)
    with pytest.raises(InvalidTransition):
        m.advance()
    with pytest.raises(InvalidTransition):
        m.transition_to(State.COMPLETE)


def test_arbitrary_jumps_rejected():
    m, _ = _machine()
    with pytest.raises(InvalidTransition):
        m.transition_to(State.PRODUCE_REPORT)


def test_cancellation_between_states():
    m, _ = _machine()
    m.advance()
    m.cancel_requested = True
    assert m.advance() == State.CANCELLED


def test_failure_transitions_defined_for_all_workflow_states():
    for state in NEXT_STATE:
        m, _ = _machine()
        m.current = state
        m.fail()
        assert m.current in TERMINAL_STATES


def test_every_terminal_state_maps_to_status():
    for terminal in TERMINAL_STATES:
        assert terminal in TERMINAL_STATUS
        assert TERMINAL_STATUS[terminal] in {
            "completed", "partially_completed", "denied",
            "failed_safely", "cancelled", "budget_exhausted",
        }
