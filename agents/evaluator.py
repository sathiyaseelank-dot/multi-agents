"""Evaluator agent for autonomous project quality assessment."""

import logging
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent
from parsing.extractor import extract_json

logger = logging.getLogger(__name__)

EVALUATOR_PROMPT_TEMPLATE = """Evaluate this generated software project.

Assess:
- correctness
- performance
- scalability
- code quality
- architecture

Project summary:
{project_summary}

Return JSON only:
{{
  "score": 0,
  "strengths": [],
  "weaknesses": [],
  "architectural_issues": [],
  "suggestions": []
}}"""


class EvaluatorAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="codex",
                role="evaluator",
                command="codex",
                subcommand="exec",
                timeout_seconds=120,
                retry_count=2,
                retry_backoff_seconds=2,
            )
        super().__init__(config)

    def build_prompt(self, task_description: str, context: Optional[dict] = None) -> str:
        return EVALUATOR_PROMPT_TEMPLATE.format(project_summary=task_description)

    def parse_output(self, raw_output: str) -> Any:
        result = extract_json(raw_output)
        if isinstance(result, dict) and "score" in result:
            return {
                "score": int(result.get("score", 0)),
                "strengths": list(result.get("strengths", [])),
                "weaknesses": list(result.get("weaknesses", [])),
                "architectural_issues": list(result.get("architectural_issues", [])),
                "suggestions": list(result.get("suggestions", [])),
            }
        return None
