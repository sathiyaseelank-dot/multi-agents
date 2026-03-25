"""Tests for the state machine."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from orchestrator.state_machine import State, StateMachine


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine()
        assert sm.state == State.INIT

    def test_valid_transitions(self):
        sm = StateMachine()
        sm.transition(State.PLANNING)
        sm.transition(State.PRE_VALIDATING)
        assert sm.state == State.PRE_VALIDATING
        sm.transition(State.EXECUTING)
        assert sm.state == State.EXECUTING
        sm.transition(State.REPLANNING)
        assert sm.state == State.REPLANNING
        sm.transition(State.BUILDING)
        assert sm.state == State.BUILDING
        sm.transition(State.VALIDATING)
        assert sm.state == State.VALIDATING
        sm.transition(State.RUNNING)
        assert sm.state == State.RUNNING
        sm.transition(State.COMPLETED)
        assert sm.state == State.COMPLETED

    def test_invalid_transition_raises(self):
        sm = StateMachine()
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(State.EXECUTING)  # Can't skip PLANNING

    def test_terminal_state(self):
        sm = StateMachine()
        sm.transition(State.PLANNING)
        sm.transition(State.COMPLETED)
        assert sm.is_terminal

    def test_fail_from_any_state(self):
        sm = StateMachine()
        sm.transition(State.PLANNING)
        sm.fail("something broke")
        assert sm.state == State.FAILED
        assert sm.is_terminal

    def test_history_tracking(self):
        sm = StateMachine()
        sm.transition(State.PLANNING)
        sm.transition(State.PRE_VALIDATING)
        assert len(sm.history) == 2
        assert sm.history[0] == (State.INIT, State.PLANNING)
        assert sm.history[1] == (State.PLANNING, State.PRE_VALIDATING)

    def test_callback_on_transition(self):
        transitions = []
        def cb(old, new):
            transitions.append((old, new))

        sm = StateMachine(on_transition=cb)
        sm.transition(State.PLANNING)
        assert len(transitions) == 1
        assert transitions[0] == (State.INIT, State.PLANNING)

    def test_cannot_transition_from_completed(self):
        sm = StateMachine()
        sm.transition(State.PLANNING)
        sm.transition(State.COMPLETED)
        with pytest.raises(ValueError):
            sm.transition(State.EXECUTING)

    def test_planning_can_skip_to_completed(self):
        """Planning phase might complete without execution (e.g., just showing the plan)."""
        sm = StateMachine()
        sm.transition(State.PLANNING)
        sm.transition(State.PRE_VALIDATING)
        sm.transition(State.COMPLETED)
        assert sm.state == State.COMPLETED
