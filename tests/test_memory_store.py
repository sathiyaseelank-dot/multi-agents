"""Tests for retrieval and persistence of orchestration memory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.memory_store import MemoryStore


def test_memory_store_round_trip(tmp_path):
    store = MemoryStore(memory_dir=str(tmp_path))
    store.add_run(
        session_id="session-1",
        prompt="Build chat app",
        refined_goal="Build chat app with auth and tests",
        errors=["Missing dependency"],
        fixes_applied=[{"summary": "Added requirements"}],
        final_score=82,
    )

    matches = store.find_similar_runs("Create a chat app")

    assert len(matches) == 1
    assert matches[0]["session_id"] == "session-1"
    assert matches[0]["final_score"] == 82
