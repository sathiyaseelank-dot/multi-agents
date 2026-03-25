"""Codex planner agents — planner and reviewer for structured task planning."""

import json
import logging
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent
from parsing.extractor import extract_json

logger = logging.getLogger(__name__)

PLANNER_PROMPT_TEMPLATE = """You are a task planner for a multi-agent development system.

Break down the following user request into concrete, actionable subtasks.
Assign each subtask to an agent role: "backend" (OpenCode), "frontend" (Gemini), or "testing" (Kilo).

IMPORTANT: Return ONLY a JSON object with this exact structure (no extra text):

```json
{{
  "epic": "<original user request>",
  "tasks": [
    {{
      "id": "task-001",
      "type": "<backend|frontend|testing>",
      "agent": "<opencode|gemini|kilo>",
      "title": "<short title>",
      "description": "<what to build/do>",
      "dependencies": []
    }}
  ],
  "phases": [
    {{
      "phase": 1,
      "description": "<what happens in this phase>",
      "parallel": true,
      "task_ids": ["task-001", "task-002"]
    }}
  ]
}}
```

Rules:
- Tasks with no dependencies can run in parallel (same phase)
- Testing tasks should depend on the code they test
- Keep tasks focused — one clear deliverable each
- Use phase numbers to indicate execution order

User request: {task_description}"""

PLANNER_REVISION_PROMPT_TEMPLATE = """You are the planner in a controlled planning debate for a multi-agent development system.

You already produced a plan. A reviewer has critiqued it. Revise the existing plan using the reviewer feedback.

Rules:
- Preserve valid parts of the previous plan whenever possible
- Modify only the parts needed to address reviewer feedback
- Do not produce commentary
- Return ONLY the full executable plan JSON with the same schema as before

User request: {task_description}

Previous plan:
```json
{prior_plan}
```

Reviewer feedback:
```json
{review_feedback}
```"""

REVIEWER_PROMPT_TEMPLATE = """You are the reviewer in a controlled planning debate for a multi-agent development system.

You MUST critique the candidate plan, not rewrite it.
You MUST NOT generate a replacement plan.

Review criteria:
- missing tasks
- dependency errors
- architectural issues
- scalability concerns

Critical issues are limited to:
- missing core task
- broken dependencies
- invalid architecture
- execution impossible

Guardrails:
- If there are no critical issues, approve the plan
- Do not over-reject minor or stylistic issues
- Keep feedback concise and actionable

Return ONLY a JSON object with this exact schema:
```json
{{
  "issues": ["..."],
  "suggestions": ["..."],
  "approval": true,
  "confidence": 0.0
}}
```

User request: {task_description}

Candidate plan:
```json
{candidate_plan}
```"""


class PlannerAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="codex",
                role="planner",
                command="codex",
                subcommand="exec",
                timeout_seconds=120,
                retry_count=3,
                retry_backoff_seconds=2,
            )
        super().__init__(config)

    def build_prompt(self, task_description: str, context: Optional[dict] = None) -> str:
        """Build the planner prompt from the template."""
        prompt = PLANNER_PROMPT_TEMPLATE.format(task_description=task_description)
        if context:
            sections = []
            goal_analysis = context.get("goal_analysis")
            if goal_analysis:
                sections.append("Goal analysis:")
                sections.append(json.dumps(goal_analysis, indent=2))
            similar_runs = context.get("similar_runs")
            if similar_runs:
                sections.append("Relevant past runs:")
                sections.append(json.dumps(similar_runs, indent=2))
            failure_feedback = context.get("failure_feedback")
            if failure_feedback:
                sections.append("Failure feedback for replanning:")
                sections.append(json.dumps(failure_feedback, indent=2))
            if not sections:
                sections.append(json.dumps(context, indent=2))
            prompt += "\n\nAdditional context:\n" + "\n".join(sections)
        return prompt

    def build_revision_prompt(
        self,
        task_description: str,
        prior_plan: dict,
        review_feedback: dict,
        context: Optional[dict] = None,
    ) -> str:
        """Build a revision prompt that preserves valid prior work."""
        prompt = PLANNER_REVISION_PROMPT_TEMPLATE.format(
            task_description=task_description,
            prior_plan=json.dumps(prior_plan, indent=2),
            review_feedback=json.dumps(review_feedback, indent=2),
        )
        if context:
            prompt += "\n\nAdditional context:\n" + json.dumps(context, indent=2)
        return prompt

    async def generate_initial_plan(
        self,
        task_description: str,
        context: Optional[dict] = None,
    ):
        return await self.execute(self.build_prompt(task_description, context=context))

    async def revise_plan(
        self,
        task_description: str,
        prior_plan: dict,
        review_feedback: dict,
        context: Optional[dict] = None,
    ):
        return await self.execute(
            self.build_revision_prompt(
                task_description,
                prior_plan,
                review_feedback,
                context=context,
            )
        )

    def parse_output(self, raw_output: str) -> Any:
        """Extract the JSON task plan from Codex output."""
        result = extract_json(raw_output)
        if result is None:
            logger.warning("Failed to extract JSON from planner output")
            return None

        # Validate minimum structure
        if isinstance(result, dict):
            if "tasks" not in result and "subtasks" not in result:
                logger.warning("Planner output missing 'tasks' or 'subtasks' key")
                return None
            # Normalize: Codex sometimes uses "subtasks" instead of "tasks"
            if "subtasks" in result and "tasks" not in result:
                result["tasks"] = result.pop("subtasks")
        return result

    def validate_plan(self, plan: dict) -> list[str]:
        """Validate a parsed plan and return any issues."""
        issues = []
        if not plan:
            return ["Plan is empty or None"]

        tasks = plan.get("tasks", [])
        if not tasks:
            issues.append("Plan has no tasks")
            return issues

        valid_agents = {"opencode", "gemini", "kilo"}
        valid_types = {"backend", "frontend", "testing"}
        task_ids = set()

        for task in tasks:
            tid = task.get("id", "")
            if not tid:
                issues.append("Task missing 'id' field")
            elif tid in task_ids:
                issues.append(f"Duplicate task id: {tid}")
            task_ids.add(tid)

            agent = task.get("agent", "")
            if agent and agent not in valid_agents:
                issues.append(f"Task {tid}: unknown agent '{agent}'")

            task_type = task.get("type", "")
            if task_type and task_type not in valid_types:
                issues.append(f"Task {tid}: unknown type '{task_type}'")

            for dep in task.get("dependencies", []):
                if dep not in task_ids and dep not in {t.get("id") for t in tasks}:
                    issues.append(f"Task {tid}: dependency '{dep}' not found in plan")

        return issues


class PlanReviewerAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="codex-reviewer",
                role="reviewer",
                command="codex",
                subcommand="exec",
                timeout_seconds=90,
                retry_count=2,
                retry_backoff_seconds=2,
            )
        super().__init__(config)

    def build_prompt(self, task_description: str, context: Optional[dict] = None) -> str:
        candidate_plan = context.get("candidate_plan", {}) if context else {}
        prompt = REVIEWER_PROMPT_TEMPLATE.format(
            task_description=task_description,
            candidate_plan=json.dumps(candidate_plan, indent=2),
        )
        if context:
            extra = {
                key: value
                for key, value in context.items()
                if key != "candidate_plan"
            }
            if extra:
                prompt += "\n\nAdditional context:\n" + json.dumps(extra, indent=2)
        return prompt

    async def review_plan(
        self,
        task_description: str,
        candidate_plan: dict,
        context: Optional[dict] = None,
    ):
        payload = dict(context or {})
        payload["candidate_plan"] = candidate_plan
        return await self.execute(self.build_prompt(task_description, context=payload))

    def parse_output(self, raw_output: str) -> Any:
        return extract_json(raw_output)
