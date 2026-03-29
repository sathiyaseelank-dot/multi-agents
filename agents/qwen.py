"""Qwen agent — code generation and assistance using Qwen models."""

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

QWEN_PROMPT_TEMPLATE = """{task_description}
{context_section}
{output_section}"""


class QwenAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            model = os.environ.get("QWEN_MODEL", "qwen-coder-plus")
            args = []
            if model:
                args.extend(["--model", model])
            config = AgentConfig(
                name="qwen",
                role="backend",  # Can be used for backend or frontend
                command="qwen",
                subcommand=None,  # Qwen uses positional prompt
                args=args,
                timeout_seconds=300,  # 5 minutes for Qwen
                retry_count=2,
                retry_backoff_seconds=5,
            )
        super().__init__(config)

    def build_command(self, prompt: str) -> list[str]:
        """Build Qwen CLI command - uses positional prompt."""
        cmd = [self.config.command]
        cmd.extend(self.config.args)
        cmd.append(prompt)
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
                parts.append("Context:")
                for ct in context["completed_tasks"]:
                    title = ct.get("title", "Unknown")
                    summary = ct.get("summary", "done")
                    parts.append(f"  - {title}: {summary}")
                    # Limit code blocks to prevent huge prompts
                    for block in ct.get("code_blocks", [])[:3]:  # Max 3 blocks
                        lang = block.get("language", "")
                        code = block.get("code", "")
                        if code:
                            # Truncate long code
                            if len(code) > 2000:
                                code = code[:1000] + "\n  ... [truncated] ...\n" + code[-1000:]
                            parts.append(f"  ```{lang}\n  {code}\n  ```")
            if context.get("workspace_files"):
                parts.append("Relevant files:")
                # Limit to first 3 files, truncate content
                for item in context["workspace_files"][:3]:
                    path = item.get("path", "")
                    content = item.get("content", "")[:1500]  # Max 1500 chars per file
                    if content:
                        parts.append(f"File: {path}")
                        parts.append(f"```text\n{content}\n```")
            if parts:
                context_section = "\n" + "\n".join(parts)

        return QWEN_PROMPT_TEMPLATE.format(
            task_description=task_description,
            context_section=context_section,
            output_section=manifest_output_instructions("src"),
        )

    def parse_output(self, raw_output: str) -> Any:
        return normalize_manifest_output(raw_output, "qwen")
