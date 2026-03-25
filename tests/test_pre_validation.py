"""Tests for pre-execution risk prediction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.pre_validation import predict_plan_risks


def test_pre_validation_predicts_missing_dependencies():
    plan = {
        "tasks": [
            {
                "id": "task-1",
                "title": "Build Flask API",
                "description": "Create a Flask backend",
                "type": "backend",
                "dependencies": [],
            }
        ]
    }

    result = predict_plan_risks(plan, "Build a Flask service")

    assert any(item["type"] == "missing_dependencies" for item in result["predictions"])


def test_pre_validation_detects_shallow_architecture():
    plan = {
        "tasks": [
            {
                "id": "task-1",
                "title": "Build UI",
                "description": "Create dashboard frontend",
                "type": "frontend",
                "dependencies": [],
            }
        ]
    }

    result = predict_plan_risks(plan, "Build a dashboard app")

    assert any(item["type"] == "bad_architecture" for item in result["predictions"])
