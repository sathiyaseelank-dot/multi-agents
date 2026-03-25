"""Tests for goal refinement heuristics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.goal_analyzer import analyze_goal


def test_goal_analyzer_expands_vague_chat_app_goal():
    result = analyze_goal("build chat app")

    assert "Include:" in result["refined_goal"]
    assert "authentication" in result["refined_goal"]
    assert "validation and test coverage" in result["refined_goal"]


def test_goal_analyzer_includes_memory_hints():
    result = analyze_goal("build api", similar_runs=[{"errors": ["Invalid import path"]}])

    assert any("Avoid prior issue" in hint for hint in result["memory_hints"])
