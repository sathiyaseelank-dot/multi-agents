"""Gemini frontend agent — generates UI components and styling."""

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

FRONTEND_PROMPT_TEMPLATE = """Write UI code for: {task_description}
{context_section}
{output_section}"""


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
            if context.get("directory_tree"):
                parts.append("Workspace tree:")
                parts.append(context["directory_tree"])
            if context.get("completed_tasks"):
                parts.append("Previously completed work:")
                for ct in context["completed_tasks"]:
                    parts.append(f"  - {ct.get('title', 'Unknown')}: {ct.get('summary', 'done')}")
            if context.get("changed_files"):
                parts.append("Changed files:")
                for item in context["changed_files"][:4]:
                    parts.append(f"  - {item['path']}")
                    if item.get("diff"):
                        parts.append(f"```diff\n{item['diff'][:2000]}\n```")
            if context.get("workspace_files"):
                parts.append("Relevant file contents:")
                for item in context["workspace_files"][:4]:
                    parts.append(f"File: {item['path']}")
                    parts.append(f"```text\n{item.get('content', '')[:3000]}\n```")
            if context.get("files_created"):
                parts.append(f"Existing files: {', '.join(context['files_created'])}")
            if parts:
                context_section = "Context:\n" + "\n".join(parts)

        return FRONTEND_PROMPT_TEMPLATE.format(
            task_description=task_description,
            context_section=context_section,
            output_section=manifest_output_instructions("frontend"),
        )

    def parse_output(self, raw_output: str) -> Any:
        return normalize_manifest_output(raw_output, "frontend")
