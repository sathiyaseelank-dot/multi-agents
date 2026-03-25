"""Predict likely failures before execution begins.

Extended with pattern-aware risk prediction using historical learning.
"""

from pathlib import Path
from typing import Optional

from .pattern_learner import PatternLearner


def predict_plan_risks(
    plan: dict,
    task_description: str,
    similar_runs: Optional[list[dict]] = None,
    pattern_learner: Optional[PatternLearner] = None,
) -> dict:
    """Predict risks with pattern-aware analysis.
    
    Args:
        plan: Task plan from planner.
        task_description: User task description.
        similar_runs: Similar historical runs.
        pattern_learner: PatternLearner instance for pattern queries.
        
    Returns:
        Risk prediction dictionary.
    """
    tasks = plan.get("tasks", [])
    warnings = []

    task_types = {task.get("type", "") for task in tasks}
    descriptions = " ".join(
        f"{task.get('title', '')} {task.get('description', '')} {task.get('type', '')}"
        for task in tasks
    ).lower()
    full_text = f"{task_description} {descriptions}".lower()

    if "flask" in full_text or "fastapi" in full_text:
        warnings.append({
            "type": "missing_dependencies",
            "message": "Backend framework detected in planning context; ensure requirements.txt includes the runtime dependency.",
        })
    if "import " in descriptions and "testing" not in task_types:
        warnings.append({
            "type": "invalid_imports",
            "message": "Plan references implementation details without explicit testing coverage for imports or package layout.",
        })
    if "frontend" in task_types and "backend" not in task_types:
        warnings.append({
            "type": "bad_architecture",
            "message": "Frontend work is planned without backend support; verify the requested architecture is complete.",
        })
    if len(tasks) <= 1 and any(keyword in full_text for keyword in ("app", "platform", "dashboard")):
        warnings.append({
            "type": "bad_architecture",
            "message": "Plan appears too shallow for the requested system and may miss core layers.",
        })

    # Add warnings from similar runs
    for run in similar_runs or []:
        for error in run.get("errors", [])[:2]:
            warnings.append({
                "type": "historical_failure",
                "message": f"Similar run previously failed with: {error}",
            })

    # Add pattern-based warnings
    if pattern_learner:
        pattern_warnings = _get_pattern_warnings(task_description, pattern_learner)
        warnings.extend(pattern_warnings)

    return {
        "success": True,
        "predictions": _dedupe_predictions(warnings),
        "summary": f"Predicted {len(_dedupe_predictions(warnings))} likely issue(s) before execution.",
    }


def _get_pattern_warnings(
    task_description: str,
    pattern_learner: PatternLearner,
) -> list[dict]:
    """Get warnings based on failure patterns.
    
    Args:
        task_description: User task description.
        pattern_learner: PatternLearner instance.
        
    Returns:
        List of pattern-based warnings.
    """
    warnings = []
    
    # Get common failures
    failure_patterns = pattern_learner.get_common_failures(limit=5)
    
    for pattern in failure_patterns:
        sig = pattern.get("signature", {})
        error_types = sig.get("error_types", [])
        keywords = sig.get("keywords", [])
        
        for error_type in error_types:
            if error_type == "import":
                warnings.append({
                    "type": "pattern_import_risk",
                    "message": f"Historical pattern: import errors occurred {pattern.get('repair_count', 1)} times. Ensure proper package structure.",
                })
            elif error_type == "syntax":
                warnings.append({
                    "type": "pattern_syntax_risk",
                    "message": "Historical pattern: syntax errors detected in prior runs. Validate generated code carefully.",
                })
            elif error_type == "dependency":
                warnings.append({
                    "type": "pattern_dependency_risk",
                    "message": "Historical pattern: dependency issues in prior runs. Verify requirements.txt completeness.",
                })
        
        for keyword in keywords:
            if keyword == "timeout":
                warnings.append({
                    "type": "pattern_timeout_risk",
                    "message": "Historical pattern: timeouts occurred. Consider simpler implementations or increased timeouts.",
                })
    
    return warnings


def predict_plan_risks_with_learning(
    plan: dict,
    task_description: str,
    similar_runs: list[dict],
    pattern_learner: PatternLearner,
) -> dict:
    """Full pattern-aware risk prediction with learning.
    
    Args:
        plan: Task plan from planner.
        task_description: User task description.
        similar_runs: Similar historical runs.
        pattern_learner: PatternLearner instance.
        
    Returns:
        Complete risk prediction.
    """
    return predict_plan_risks(
        plan,
        task_description,
        similar_runs=similar_runs,
        pattern_learner=pattern_learner,
    )


def infer_architecture_signals(project_dir: str) -> dict:
    """Infer architecture signals from project structure.
    
    Args:
        project_dir: Project directory path.
        
    Returns:
        Architecture signals dictionary.
    """
    root = Path(project_dir)
    return {
        "has_backend": (root / "backend").exists(),
        "has_frontend": (root / "frontend").exists(),
        "has_tests": (root / "tests").exists(),
    }


def _dedupe_predictions(predictions: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in predictions:
        key = (item.get("type", ""), item.get("message", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
