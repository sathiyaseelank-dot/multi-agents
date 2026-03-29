"""Kilo testing agent — generates tests and validates code."""

import logging
import os
from typing import Any, Optional

from .base_agent import (
    AgentConfig,
    BaseAgent,
    manifest_output_instructions,
    normalize_manifest_output,
)

logger = logging.getLogger(__name__)

TESTING_PROMPT_TEMPLATE = """Write tests for: {task_description}
{context_section}
{output_section}"""


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
                timeout_seconds=600,  # 10 minutes for complex test generation
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
            if context.get("directory_tree"):
                parts.append("Workspace tree:")
                parts.append(context["directory_tree"])
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
            if context.get("workspace_files"):
                parts.append("Relevant file contents:")
                for item in context["workspace_files"][:4]:
                    parts.append(f"File: {item['path']}")
                    parts.append(f"```text\n{item.get('content', '')[:3000]}\n```")
            if parts:
                context_section = "Context:\n" + "\n".join(parts)

        return TESTING_PROMPT_TEMPLATE.format(
            task_description=task_description,
            context_section=context_section,
            output_section=manifest_output_instructions("tests"),
        )

    def parse_output(self, raw_output: str) -> Any:
        return normalize_manifest_output(raw_output, "testing")
