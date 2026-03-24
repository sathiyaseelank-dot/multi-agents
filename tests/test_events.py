"""Unit tests for structured event emission."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.events import EventEmitter, EventType


class TestEventEmitter:
    def test_emit_adds_required_fields(self):
        emitter = EventEmitter(session_id="session-1", writer=lambda _: None)

        event = emitter.emit(EventType.TASK_STARTED, {"task_id": "task-001"})

        assert event.type == EventType.TASK_STARTED.value
        assert event.session_id == "session-1"
        assert event.timestamp
        assert event.data["task_id"] == "task-001"

    def test_history_is_bounded(self):
        emitter = EventEmitter(session_id="session-1", max_history=2, writer=lambda _: None)

        emitter.emit(EventType.INFO, {"message": "one"})
        emitter.emit(EventType.INFO, {"message": "two"})
        emitter.emit(EventType.INFO, {"message": "three"})

        history = emitter.get_history()
        assert len(history) == 2
        assert history[0]["data"]["message"] == "two"
        assert history[1]["data"]["message"] == "three"

    def test_summary_only_suppresses_task_render_not_history(self):
        lines = []
        emitter = EventEmitter(
            session_id="session-1",
            summary_only=True,
            writer=lines.append,
        )

        emitter.emit(EventType.TASK_STARTED, {"task_id": "task-001", "title": "Demo", "agent": "opencode"})

        assert emitter.get_history()[0]["type"] == EventType.TASK_STARTED.value
        assert lines == []
