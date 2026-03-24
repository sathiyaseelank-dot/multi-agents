"""Kilo testing agent — generates tests and validates code."""

import logging
import os
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent
from parsing.extractor import extract_json, extract_code_blocks

logger = logging.getLogger(__name__)

TESTING_PROMPT_TEMPLATE = """Write tests for: {task_description}
{context_section}
Put test code in fenced blocks with language tags."""


class TesterAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            model = os.environ.get("KILO_MODEL", "")
            args = ["--auto"]
            if model:
                args.extend(["--model", model])
            config = AgentConfig(
                name="kilo",
                role="testing",
                command="kilo",
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
                parts.append("Code to test:")
                for ct in context["completed_tasks"]:
                    title = ct.get("title", "Unknown")
                    summary = ct.get("summary", "done")
                    parts.append(f"  - {title}: {summary}")
                    # Include actual code snippets if available
                    for block in ct.get("code_blocks", []):
                        lang = block.get("language", "")
                        code = block.get("code", "")
                        if code:
                            parts.append(f"  ```{lang}\n  {code}\n  ```")
            if parts:
                context_section = "Context:\n" + "\n".join(parts)

        return TESTING_PROMPT_TEMPLATE.format(
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
                "summary": f"Generated {len(blocks)} test block(s)",
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
