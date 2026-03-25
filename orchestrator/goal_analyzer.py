"""Refine user goals into clearer implementation intents.

Extended with learning-aware analysis using historical patterns.
"""

from typing import Optional

from .pattern_learner import PatternLearner
from .strategy_scorer import StrategyScorer

VAGUE_HINTS = {
    "chat app": ["authentication", "message persistence", "backend API", "frontend UI", "basic deployment notes"],
    "dashboard": ["data source integration", "stateful UI", "error handling", "tests"],
    "api": ["request validation", "error handling", "tests", "dependency manifest"],
}


def analyze_goal(
    task_description: str,
    similar_runs: Optional[list[dict]] = None,
    pattern_learner: Optional[PatternLearner] = None,
    strategy_scorer: Optional[StrategyScorer] = None,
) -> dict:
    """Analyze and refine user goal with learning integration.
    
    Args:
        task_description: Original user task description.
        similar_runs: Similar historical runs.
        pattern_learner: PatternLearner instance for pattern queries.
        strategy_scorer: StrategyScorer instance for strategy recommendations.
        
    Returns:
        Analysis dictionary with refined goal and learning hints.
    """
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

    # Add learning-based hints
    learning_hints = []
    framework_recommendations = []
    
    if pattern_learner:
        # Get recommended frameworks from patterns
        recommended = pattern_learner.get_recommended_frameworks(task_description)
        if recommended:
            framework_recommendations = recommended[:3]
            learning_hints.append(f"Recommended frameworks based on success: {', '.join(recommended[:3])}")
        
        # Get success patterns
        success_patterns = pattern_learner.get_success_patterns(min_score=75, limit=2)
        for pattern in success_patterns:
            sig = pattern.get("signature", {})
            if sig.get("no_repairs"):
                learning_hints.append("Aim for clean generation without repairs (proven success pattern)")
                break
    
    if strategy_scorer:
        # Get strategy recommendations
        recs = strategy_scorer.get_recommendations(task_description)
        if recs.get("frameworks"):
            top_fw = recs["frameworks"][0]
            learning_hints.append(
                f"Best performing framework: {top_fw['strategy']} "
                f"(score: {top_fw['adjusted_score']:.2f})"
            )
    
    return {
        "original_goal": task_description,
        "refined_goal": refined,
        "expansions": expansions,
        "memory_hints": memory_hints,
        "learning_hints": learning_hints,
        "framework_recommendations": framework_recommendations,
    }


def analyze_goal_with_learning(
    task_description: str,
    pattern_learner: PatternLearner,
    strategy_scorer: StrategyScorer,
    similar_runs: Optional[list[dict]] = None,
) -> dict:
    """Full learning-aware goal analysis.
    
    Args:
        task_description: Original user task description.
        pattern_learner: PatternLearner instance.
        strategy_scorer: StrategyScorer instance.
        similar_runs: Similar historical runs.
        
    Returns:
        Complete analysis with all learning data.
    """
    return analyze_goal(
        task_description,
        similar_runs=similar_runs,
        pattern_learner=pattern_learner,
        strategy_scorer=strategy_scorer,
    )


def _dedupe(items: list[str]) -> list[str]:
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen
