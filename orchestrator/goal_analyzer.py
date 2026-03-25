"""Refine user goals into clearer implementation intents."""

from typing import Optional


VAGUE_HINTS = {
    "chat app": ["authentication", "message persistence", "backend API", "frontend UI", "basic deployment notes"],
    "dashboard": ["data source integration", "stateful UI", "error handling", "tests"],
    "api": ["request validation", "error handling", "tests", "dependency manifest"],
}


def analyze_goal(task_description: str, similar_runs: Optional[list[dict]] = None) -> dict:
    refined = task_description.strip()
    expansions = []
    lowered = refined.lower()

    for hint, items in VAGUE_HINTS.items():
        if hint in lowered:
            expansions.extend(items)

    if "auth" not in lowered and any(word in lowered for word in ("app", "platform", "service")):
        expansions.append("basic authentication or access assumptions")
    if "test" not in lowered:
        expansions.append("validation and test coverage")

    expansions = _dedupe(expansions)
    if expansions:
        refined = f"{refined}. Include: {', '.join(expansions)}."

    memory_hints = []
    for run in similar_runs or []:
        for error in run.get("errors", [])[:2]:
            memory_hints.append(f"Avoid prior issue: {error}")
    memory_hints = _dedupe(memory_hints)

    return {
        "original_goal": task_description,
        "refined_goal": refined,
        "expansions": expansions,
        "memory_hints": memory_hints,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen
