"""DAG-aware task routing — compute execution order and handle fallbacks."""

import logging
from typing import Optional

from .task_manager import Task, TaskManager, TaskStatus

logger = logging.getLogger(__name__)

# Fallback agents when the primary fails
FALLBACK_MAP = {
    "opencode": ["gemini", "kilo"],
    "gemini": ["opencode", "kilo"],
    "kilo": ["opencode", "gemini"],
}

# Agent capabilities — what each can reasonably handle
AGENT_CAPABILITIES = {
    "opencode": {"backend", "testing", "frontend"},
    "gemini": {"frontend", "backend", "testing"},
    "kilo": {"testing"},
}


def compute_phases(tasks: list[Task]) -> list[list[Task]]:
    """Compute execution phases from task dependencies using topological sort.

    Returns a list of phases, where each phase is a list of tasks
    that can run in parallel (all dependencies satisfied by prior phases).
    """
    task_map = {t.id: t for t in tasks}
    task_order = [t.id for t in tasks]
    remaining = set(t.id for t in tasks)
    completed = set()
    phases = []

    max_iterations = len(tasks) + 1
    for _ in range(max_iterations):
        if not remaining:
            break

        # Find tasks whose dependencies are all completed
        ready = []
        for tid in task_order:
            if tid not in remaining:
                continue
            task = task_map[tid]
            deps = set(task.dependencies)
            if deps.issubset(completed):
                ready.append(task)

        if not ready:
            # Circular dependency or unresolvable deps
            unresolved = [task_map[tid] for tid in remaining]
            logger.warning(
                f"Cannot resolve dependencies for: {[t.id for t in unresolved]}"
            )
            # Add them as a final phase anyway
            phases.append(unresolved)
            break

        phases.append(ready)
        for task in ready:
            remaining.discard(task.id)
            completed.add(task.id)

    return phases


def build_phase_payloads(phases: list[list[Task]]) -> list[dict]:
    """Build canonical, UI-friendly phase metadata from computed phases."""
    payloads = []
    for index, phase in enumerate(phases, 1):
        task_ids = [task.id for task in phase]
        parallel = len(phase) > 1
        description = (
            f"Run {', '.join(task_ids)} in parallel"
            if parallel
            else f"Run {task_ids[0]}"
            if task_ids
            else "No tasks"
        )
        payloads.append(
            {
                "phase": index,
                "description": description,
                "parallel": parallel,
                "task_ids": task_ids,
                "agents": [task.agent for task in phase],
            }
        )
    return payloads


def get_fallback_agent(
    failed_agent: str,
    task_type: str,
    excluded_agents: set[str] | None = None,
) -> Optional[str]:
    """Get a fallback agent when the primary fails.

    Returns the best alternative agent name, or None if no fallback available.
    """
    excluded = excluded_agents or set()
    fallbacks = FALLBACK_MAP.get(failed_agent, [])
    for agent in fallbacks:
        if agent in excluded:
            continue
        caps = AGENT_CAPABILITIES.get(agent, set())
        if task_type in caps:
            return agent
    return None


def compute_execution_summary(phases: list[list[Task]]) -> str:
    """Generate a human-readable execution summary."""
    lines = []
    for i, phase in enumerate(phases, 1):
        parallel = len(phase) > 1
        mode = "parallel" if parallel else "sequential"
        task_ids = ", ".join(t.id for t in phase)
        agents = ", ".join(sorted(set(t.agent for t in phase)))
        lines.append(f"  Phase {i} ({mode}): [{task_ids}] via {agents}")
    return "\n".join(lines)
