"""State machine for orchestration workflow."""

from enum import Enum
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class State(Enum):
    INIT = "INIT"
    PLANNING = "PLANNING"
    PRE_VALIDATING = "PRE_VALIDATING"
    EXECUTING = "EXECUTING"
    REPLANNING = "REPLANNING"
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    REPAIRING = "REPAIRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Valid transitions: from_state -> set of allowed to_states
TRANSITIONS = {
    State.INIT: {State.PLANNING, State.FAILED},
    State.PLANNING: {State.PRE_VALIDATING, State.EXECUTING, State.COMPLETED, State.FAILED},
    State.PRE_VALIDATING: {State.EXECUTING, State.COMPLETED, State.FAILED},
    State.EXECUTING: {State.REPLANNING, State.BUILDING, State.FAILED},
    State.REPLANNING: {State.EXECUTING, State.BUILDING, State.FAILED},
    State.BUILDING: {State.VALIDATING, State.FAILED},
    State.VALIDATING: {State.RUNNING, State.REPAIRING, State.FAILED},
    State.RUNNING: {State.COMPLETED, State.REPAIRING, State.FAILED},
    State.REPAIRING: {State.VALIDATING, State.RUNNING, State.FAILED},
    State.COMPLETED: set(),
    State.FAILED: set(),
}


class StateMachine:
    def __init__(self, on_transition: Optional[Callable] = None):
        self._state = State.INIT
        self._on_transition = on_transition
        self._history: list[tuple[State, State]] = []

    @property
    def state(self) -> State:
        return self._state

    @property
    def history(self) -> list[tuple[State, State]]:
        return list(self._history)

    @property
    def is_terminal(self) -> bool:
        return self._state in (State.COMPLETED, State.FAILED)

    def transition(self, new_state: State) -> None:
        """Transition to a new state. Raises ValueError if invalid."""
        allowed = TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self._state.value} -> {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        old_state = self._state
        self._state = new_state
        self._history.append((old_state, new_state))
        logger.info(f"State: {old_state.value} -> {new_state.value}")

        if self._on_transition:
            self._on_transition(old_state, new_state)

    def fail(self, reason: str = "") -> None:
        """Transition to FAILED state from any non-terminal state."""
        if self.is_terminal:
            return
        logger.error(f"Failing from {self._state.value}: {reason}")
        old_state = self._state
        self._state = State.FAILED
        self._history.append((old_state, State.FAILED))
        if self._on_transition:
            self._on_transition(old_state, State.FAILED)
