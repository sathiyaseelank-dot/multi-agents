"""Patcher Agent — Creates surgical code patches instead of full rewrites."""

import logging
import os
import re
from typing import Any, Optional

from .base_agent import (
    AgentConfig,
    BaseAgent,
)

logger = logging.getLogger(__name__)

PATCH_PROMPT_TEMPLATE = """You are a surgical code repair specialist. Fix ONLY the specific issue described.

**File:** {file_path}
**Lines:** {line_start}-{line_end}
**Error:** {error_message}

**Current code (lines {line_start}-{line_end}):**
```{language}
{code_context}
```

**Your task:**
Return ONLY the corrected code block for lines {line_start}-{line_end}.
- Do NOT rewrite the entire file
- Do NOT add explanations
- Do NOT include markdown fences
- Preserve indentation from the original code
- Fix ONLY the specific error mentioned

**Corrected code:**
"""


class PatcherAgent(BaseAgent):
    """Specialized agent for surgical code fixes.
    
    Unlike other agents that rewrite entire files, this agent
    creates minimal, targeted patches to fix specific issues.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            model = os.environ.get("QWEN_MODEL", "qwen-coder-plus")
            config = AgentConfig(
                name="qwen-patcher",
                role="patcher",
                command="qwen",
                subcommand=None,  # Positional prompt
                args=["--model", model] if model else [],
                timeout_seconds=120,  # Faster than full rewrite (180s)
                retry_count=2,
                retry_backoff_seconds=3,  # Faster retry
            )
        super().__init__(config)

    def build_command(self, prompt: str) -> list[str]:
        """Build Qwen CLI command - uses positional prompt."""
        cmd = [self.config.command]
        cmd.extend(self.config.args)
        cmd.append(prompt)
        return cmd

    def build_prompt(
        self,
        file_path: str,
        code_context: str,
        line_start: int,
        line_end: int,
        error_message: str,
        language: str = "python"
    ) -> str:
        """Build focused patch prompt.
        
        Args:
            file_path: Path to the file being patched
            code_context: The code lines that need fixing
            line_start: Starting line number (0-indexed)
            line_end: Ending line number (exclusive)
            error_message: Description of the error
            language: Programming language for syntax highlighting
        
        Returns:
            Prompt string for the AI agent
        """
        return PATCH_PROMPT_TEMPLATE.format(
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            error_message=error_message,
            code_context=code_context,
            language=language,
        )

    def parse_output(self, raw_output: str) -> Any:
        """Parse patch output - extract just the code block.
        
        The agent should return only code, but we handle markdown
        fences just in case.
        """
        # Remove markdown fences if present
        code = raw_output.strip()
        
        # Extract from ```language ... ``` blocks
        match = re.search(r'```(?:\w+)?\n(.*?)```', code, re.DOTALL)
        if match:
            code = match.group(1).strip()
        
        # Remove any trailing explanations
        lines = code.split('\n')
        clean_lines = []
        for line in lines:
            # Stop at first non-code line
            if line.startswith('```') or line.startswith('Return') or line.startswith('Note:'):
                break
            clean_lines.append(line)
        
        return '\n'.join(clean_lines)

    @staticmethod
    def extract_patch_info(raw_output: str, line_start: int, line_end: int) -> dict:
        """Extract structured patch information from agent output.
        
        Returns:
            Dict with 'new_code', 'line_start', 'line_end'
        """
        # Parse output to get just the code
        code_match = re.search(r'```(?:\w+)?\n(.*?)```', raw_output, re.DOTALL)
        if code_match:
            new_code = code_match.group(1).strip()
        else:
            # Take everything after the last "```" or just use raw output
            parts = raw_output.split('```')
            new_code = parts[-1].strip() if len(parts) > 1 else raw_output.strip()
        
        return {
            'new_code': new_code,
            'line_start': line_start,
            'line_end': line_end,
        }
