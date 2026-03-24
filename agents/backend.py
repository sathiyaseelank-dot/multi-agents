"""OpenCode backend agent — generates server-side code."""

import logging
import os
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent
from parsing.extractor import extract_json, extract_code_blocks

logger = logging.getLogger(__name__)

BACKEND_PROMPT_TEMPLATE = """Write code for: {task_description}
{context_section}
Put code in fenced blocks with language tags."""


class BackendAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            # Allow model override via env var
            model = os.environ.get("OPENCODE_MODEL", "")
            args = ["--model", model] if model else []
            config = AgentConfig(
                name="opencode",
                role="backend",
                command="opencode",
                subcommand="run",
                args=args,
                timeout_seconds=180,
                retry_count=2,
                retry_backoff_seconds=5,
            )
        super().__init__(config)

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

        return BACKEND_PROMPT_TEMPLATE.format(
            task_description=task_description,
            context_section=context_section,
        )

    def parse_output(self, raw_output: str) -> Any:
        """Parse OpenCode output — extract code blocks and any JSON."""
        # Try JSON first (in case output format was JSON)
        json_result = extract_json(raw_output)
        if json_result and isinstance(json_result, dict) and json_result.get("code"):
            return json_result

        # Extract code blocks
        blocks = extract_code_blocks(raw_output)
        if blocks:
            return {
                "code_blocks": blocks,
                "summary": f"Generated {len(blocks)} code block(s)",
                "files_created": [],
            }

        # Fallback: treat entire cleaned output as result
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
