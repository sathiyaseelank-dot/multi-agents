"""Gemini frontend agent — generates UI components and styling."""

import logging
import os
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent
from parsing.extractor import extract_json, extract_code_blocks

logger = logging.getLogger(__name__)

FRONTEND_PROMPT_TEMPLATE = """Write UI code for: {task_description}
{context_section}
Put code in fenced blocks with language tags."""


class FrontendAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            model = os.environ.get("GEMINI_MODEL", "")
            config = AgentConfig(
                name="gemini",
                role="frontend",
                command="gemini",
                timeout_seconds=300,
                retry_count=2,
                retry_backoff_seconds=5,
            )
            if model:
                config.args = ["-m", model]
        super().__init__(config)

    def build_command(self, prompt: str) -> list[str]:
        """Gemini uses -p flag for non-interactive mode."""
        cmd = [self.config.command, "-p", prompt]
        cmd.extend(self.config.args)
        return cmd

    def build_prompt(self, task_description: str, context: Optional[dict] = None) -> str:
        context_section = ""
        if context:
            parts = []
            if context.get("epic"):
                parts.append(f"Project: {context['epic']}")
            if context.get("completed_tasks"):
                parts.append("Previously completed work:")
                for ct in context["completed_tasks"]:
                    parts.append(f"  - {ct.get('title', 'Unknown')}: {ct.get('summary', 'done')}")
            if context.get("files_created"):
                parts.append(f"Existing files: {', '.join(context['files_created'])}")
            if parts:
                context_section = "Context:\n" + "\n".join(parts)

        return FRONTEND_PROMPT_TEMPLATE.format(
            task_description=task_description,
            context_section=context_section,
        )

    def parse_output(self, raw_output: str) -> Any:
        json_result = extract_json(raw_output)
        if json_result and isinstance(json_result, dict) and json_result.get("code"):
            return json_result

        blocks = extract_code_blocks(raw_output)
        if blocks:
            return {
                "code_blocks": blocks,
                "summary": f"Generated {len(blocks)} code block(s)",
                "files_created": [],
            }

        from parsing.sanitizer import clean_output
        cleaned = clean_output(raw_output)
        if cleaned:
            return {
                "raw_text": cleaned,
                "summary": "Raw text output (no code blocks detected)",
                "code_blocks": [],
                "files_created": [],
            }
        return None
