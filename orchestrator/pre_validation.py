"""Predict likely failures before execution begins."""

from pathlib import Path


def predict_plan_risks(plan: dict, task_description: str, similar_runs: list[dict] | None = None) -> dict:
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

    for run in similar_runs or []:
        for error in run.get("errors", [])[:2]:
            warnings.append({
                "type": "historical_failure",
                "message": f"Similar run previously failed with: {error}",
            })

    return {
        "success": True,
        "predictions": _dedupe_predictions(warnings),
        "summary": f"Predicted {len(_dedupe_predictions(warnings))} likely issue(s) before execution.",
    }


def infer_architecture_signals(project_dir: str) -> dict:
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
