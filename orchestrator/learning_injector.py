"""Learning injector for biasing planning decisions based on historical patterns.

This module injects learned patterns into the planning phase to:
- Recommend proven architectures
- Bias toward successful frameworks
- Warn against failure-prone approaches
"""

from __future__ import annotations

import logging
from typing import Optional

from .pattern_learner import PatternLearner, PATTERN_ARCHITECTURE, PATTERN_FAILURE, PATTERN_SUCCESS

logger = logging.getLogger(__name__)

# Architecture recommendation templates
ARCHITECTURE_HINTS = {
    "flask": "Consider Flask for simple REST APIs and CRUD applications - proven success pattern.",
    "fastapi": "Consider FastAPI for async APIs and high-performance requirements - highest success rate.",
    "django": "Consider Django for complex applications requiring ORM and admin interface.",
    "react": "Consider React for interactive UIs with complex state management.",
    "vue": "Consider Vue for simpler frontend needs with gentle learning curve.",
}

# Failure avoidance hints
FAILURE_HINTS = {
    "import": "Previous runs had import errors - ensure proper package structure with __init__.py files.",
    "syntax": "Previous runs had syntax errors - validate generated code before writing.",
    "dependency": "Previous runs had dependency issues - ensure requirements.txt is complete.",
    "runtime": "Previous runs had runtime failures - verify server startup and health checks.",
    "timeout": "Previous runs timed out - consider simpler implementations or increased timeouts.",
}


def build_learning_context(
    task_description: str,
    pattern_learner: PatternLearner,
    max_architecture_hints: int = 3,
    max_failure_hints: int = 3,
    max_success_hints: int = 2,
) -> dict:
    """Build a learning context from historical patterns.
    
    Args:
        task_description: The user's task description.
        pattern_learner: PatternLearner instance for querying patterns.
        max_architecture_hints: Maximum architecture hints to include.
        max_failure_hints: Maximum failure warnings to include.
        max_success_hints: Maximum success patterns to include.
        
    Returns:
        Dictionary with learning context for planning.
    """
    context = {
        "recommended_frameworks": [],
        "architecture_hints": [],
        "failure_warnings": [],
        "success_patterns": [],
        "planning_bias": {},
    }
    
    # Get recommended frameworks
    recommended = pattern_learner.get_recommended_frameworks(task_description)
    context["recommended_frameworks"] = recommended[:5]
    
    # Get similar architecture patterns
    arch_patterns = pattern_learner.get_similar_architecture_patterns(
        task_description,
        limit=max_architecture_hints
    )
    
    for pattern in arch_patterns:
        signature = pattern.get("signature", {})
        frameworks = signature.get("frameworks", [])
        
        for fw in frameworks:
            if fw in ARCHITECTURE_HINTS:
                hint = {
                    "framework": fw,
                    "hint": ARCHITECTURE_HINTS[fw],
                    "success_rate": pattern.get("success", False),
                    "score": pattern.get("score", 0),
                }
                if hint not in context["architecture_hints"]:
                    context["architecture_hints"].append(hint)
    
    # Get common failures to avoid
    failure_patterns = pattern_learner.get_common_failures(limit=max_failure_hints)
    
    for pattern in failure_patterns:
        signature = pattern.get("signature", {})
        error_types = signature.get("error_types", [])
        keywords = signature.get("keywords", [])
        
        for error_type in error_types:
            if error_type in FAILURE_HINTS:
                context["failure_warnings"].append({
                    "type": error_type,
                    "warning": FAILURE_HINTS[error_type],
                    "occurrences": pattern.get("repair_count", 1),
                })
        
        for keyword in keywords:
            if keyword in FAILURE_HINTS:
                context["failure_warnings"].append({
                    "type": keyword,
                    "warning": FAILURE_HINTS[keyword],
                    "occurrences": 1,
                })
    
    # Get success patterns
    success_patterns = pattern_learner.get_success_patterns(min_score=70, limit=max_success_hints)
    
    for pattern in success_patterns:
        signature = pattern.get("signature", {})
        if signature.get("no_repairs"):
            context["success_patterns"].append({
                "type": "clean_generation",
                "hint": "Clean generation without repairs achieved high scores previously.",
                "score": pattern.get("score", 0),
            })
        if signature.get("high_score"):
            context["success_patterns"].append({
                "type": "high_quality",
                "hint": "High evaluation scores achieved with similar approaches.",
                "score": pattern.get("score", 0),
            })
    
    # Build planning bias
    if context["recommended_frameworks"]:
        context["planning_bias"]["preferred_frameworks"] = context["recommended_frameworks"][:3]
    
    if context["failure_warnings"]:
        context["planning_bias"]["avoid_patterns"] = [
            w["type"] for w in context["failure_warnings"]
        ]
    
    return context


def inject_architecture_hints(
    task_description: str,
    patterns: list[dict],
) -> list[str]:
    """Inject architecture hints based on learned patterns.
    
    Args:
        task_description: The user's task description.
        patterns: List of architecture patterns.
        
    Returns:
        List of architecture hint strings.
    """
    hints = []
    
    for pattern in patterns:
        signature = pattern.get("signature", {})
        frameworks = signature.get("frameworks", [])
        
        for fw in frameworks:
            if fw in ARCHITECTURE_HINTS and ARCHITECTURE_HINTS[fw] not in hints:
                hints.append(ARCHITECTURE_HINTS[fw])
    
    return hints


def inject_framework_bias(patterns: list[dict]) -> dict[str, float]:
    """Compute framework bias scores from patterns.
    
    Args:
        patterns: List of architecture patterns.
        
    Returns:
        Dictionary mapping frameworks to bias scores (0.0-1.0).
    """
    framework_scores = {}
    
    for pattern in patterns:
        signature = pattern.get("signature", {})
        frameworks = signature.get("frameworks", [])
        success = pattern.get("success", False)
        score = pattern.get("score", 0)
        
        for fw in frameworks:
            if fw not in framework_scores:
                framework_scores[fw] = {"successes": 0, "total": 0, "scores": []}
            
            framework_scores[fw]["total"] += 1
            if success:
                framework_scores[fw]["successes"] += 1
            framework_scores[fw]["scores"].append(score)
    
    # Compute bias scores
    bias = {}
    for fw, stats in framework_scores.items():
        if stats["total"] > 0:
            success_rate = stats["successes"] / stats["total"]
            avg_score = sum(stats["scores"]) / len(stats["scores"]) / 100
            bias[fw] = (success_rate + avg_score) / 2
    
    return bias


def inject_avoidance_hints(failure_patterns: list[dict]) -> list[str]:
    """Generate hints about what to avoid based on failure patterns.
    
    Args:
        failure_patterns: List of failure patterns.
        
    Returns:
        List of avoidance hint strings.
    """
    hints = []
    seen_types = set()
    
    for pattern in failure_patterns:
        signature = pattern.get("signature", {})
        error_types = signature.get("error_types", [])
        keywords = signature.get("keywords", [])
        
        for error_type in error_types:
            if error_type not in seen_types and error_type in FAILURE_HINTS:
                hints.append(FAILURE_HINTS[error_type])
                seen_types.add(error_type)
        
        for keyword in keywords:
            if keyword not in seen_types and keyword in FAILURE_HINTS:
                hints.append(FAILURE_HINTS[keyword])
                seen_types.add(keyword)
    
    return hints


def build_learning_prompt_suffix(learning_context: dict) -> str:
    """Build a prompt suffix to inject learning into planner prompts.
    
    Args:
        learning_context: Learning context from build_learning_context().
        
    Returns:
        String to append to planner prompts.
    """
    sections = []
    
    # Framework recommendations
    if learning_context.get("recommended_frameworks"):
        frameworks = ", ".join(learning_context["recommended_frameworks"][:3])
        sections.append(f"RECOMMENDED FRAMEWORKS: Based on historical success, consider: {frameworks}")
    
    # Architecture hints
    if learning_context.get("architecture_hints"):
        hints = "\n".join(
            f"  - {h['hint']}" for h in learning_context["architecture_hints"][:3]
        )
        sections.append(f"ARCHITECTURE GUIDANCE:\n{hints}")
    
    # Failure warnings
    if learning_context.get("failure_warnings"):
        warnings = "\n".join(
            f"  - ⚠️ {w['warning']}" for w in learning_context["failure_warnings"][:3]
        )
        sections.append(f"AVOID PREVIOUS FAILURES:\n{warnings}")
    
    # Success patterns
    if learning_context.get("success_patterns"):
        patterns = "\n".join(
            f"  - ✓ {p['hint']}" for p in learning_context["success_patterns"][:2]
        )
        sections.append(f"PROVEN SUCCESS PATTERNS:\n{patterns}")
    
    if not sections:
        return ""
    
    return "\n\n--- LEARNING FROM EXPERIENCE ---\n" + "\n\n".join(sections) + "\n--- END LEARNING ---\n"


def augment_planner_prompt(
    base_prompt: str,
    learning_context: dict,
) -> str:
    """Augment a planner prompt with learning context.
    
    Args:
        base_prompt: The original planner prompt.
        learning_context: Learning context to inject.
        
    Returns:
        Augmented prompt with learning injected.
    """
    suffix = build_learning_prompt_suffix(learning_context)
    if not suffix:
        return base_prompt
    
    return base_prompt + suffix


class LearningInjector:
    """High-level interface for learning injection."""
    
    def __init__(self, pattern_learner: PatternLearner):
        self.pattern_learner = pattern_learner
    
    def prepare_for_planning(self, task_description: str) -> dict:
        """Prepare learning context before planning.
        
        Args:
            task_description: The user's task description.
            
        Returns:
            Learning context dictionary.
        """
        return build_learning_context(
            task_description,
            self.pattern_learner
        )
    
    def inject_into_prompt(self, base_prompt: str, learning_context: dict) -> str:
        """Inject learning into a planner prompt.
        
        Args:
            base_prompt: Original planner prompt.
            learning_context: Learning context from prepare_for_planning().
            
        Returns:
            Augmented prompt.
        """
        return augment_planner_prompt(base_prompt, learning_context)
    
    def get_recommendations(self, task_description: str) -> dict:
        """Get all recommendations for a task.
        
        Args:
            task_description: The user's task description.
            
        Returns:
            Dictionary with all recommendation types.
        """
        context = self.prepare_for_planning(task_description)
        
        return {
            "frameworks": context.get("recommended_frameworks", []),
            "architecture_hints": context.get("architecture_hints", []),
            "warnings": context.get("failure_warnings", []),
            "success_patterns": context.get("success_patterns", []),
            "planning_bias": context.get("planning_bias", {}),
        }
