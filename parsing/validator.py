"""Schema validation for agent responses."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def validate_plan(plan: Any) -> list[str]:
    """Validate a planner response. Returns list of issues (empty = valid)."""
    issues = []
    if not isinstance(plan, dict):
        return ["Plan must be a dict"]

    tasks = plan.get("tasks", plan.get("subtasks", []))
    if not tasks:
        issues.append("Plan has no tasks")
        return issues

    valid_agents = {"opencode", "gemini", "kilo"}
    valid_types = {"backend", "frontend", "testing"}
    seen_ids = set()

    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            issues.append(f"Task {i}: not a dict")
            continue

        tid = task.get("id", "")
        if not tid:
            issues.append(f"Task {i}: missing 'id'")
        elif tid in seen_ids:
            issues.append(f"Duplicate task id: {tid}")
        seen_ids.add(tid)

        if not task.get("title") and not task.get("description"):
            issues.append(f"Task {tid or i}: missing both title and description")

        agent = task.get("agent", "")
        if agent and agent not in valid_agents:
            issues.append(f"Task {tid}: unknown agent '{agent}'")

        ttype = task.get("type", "")
        if ttype and ttype not in valid_types:
            issues.append(f"Task {tid}: unknown type '{ttype}'")

    return issues


def validate_worker_result(result: Any) -> list[str]:
    """Validate a worker agent response. Returns list of issues."""
    issues = []
    if result is None:
        return ["Result is None"]

    if isinstance(result, dict):
        # Structured result — check for expected fields
        if not result.get("code") and not result.get("files_created") and not result.get("summary"):
            issues.append("Worker result has no code, files_created, or summary")
    elif isinstance(result, list):
        # Code blocks list
        for i, block in enumerate(result):
            if not isinstance(block, dict):
                issues.append(f"Code block {i}: not a dict")
            elif not block.get("code"):
                issues.append(f"Code block {i}: empty code")
    elif isinstance(result, str):
        if not result.strip():
            issues.append("Worker result is empty string")
    else:
        issues.append(f"Unexpected result type: {type(result).__name__}")

    return issues


def validate_review_feedback(review: Any) -> list[str]:
    """Validate reviewer feedback for the planning debate loop."""
    if not isinstance(review, dict):
        return ["Review feedback must be a dict"]

    issues = []

    review_issues = review.get("issues")
    if not isinstance(review_issues, list) or not all(isinstance(item, str) for item in review_issues):
        issues.append("Review feedback 'issues' must be a list of strings")

    suggestions = review.get("suggestions")
    if not isinstance(suggestions, list) or not all(isinstance(item, str) for item in suggestions):
        issues.append("Review feedback 'suggestions' must be a list of strings")

    approval = review.get("approval")
    if not isinstance(approval, bool):
        issues.append("Review feedback 'approval' must be a boolean")

    confidence = review.get("confidence")
    if not isinstance(confidence, (int, float)):
        issues.append("Review feedback 'confidence' must be a number")
    elif confidence < 0.0 or confidence > 1.0:
        issues.append("Review feedback 'confidence' must be between 0.0 and 1.0")

    return issues
