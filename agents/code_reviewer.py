"""Code Reviewer Agent — Analyzes generated code for bugs, security issues, and quality."""

import logging
import os
from typing import Any, Optional

from .base_agent import (
    AgentConfig,
    BaseAgent,
)

logger = logging.getLogger(__name__)

CODE_REVIEW_PROMPT_TEMPLATE = """You are an expert code reviewer analyzing a completed software project.

**Project:** {project_name}

**Original Request:** {original_request}

**Generated Files:**
{file_contents}

**Your Task:**
Perform a comprehensive code review focusing on:

1. **Bug Detection**
   - Logic errors
   - Edge cases not handled
   - Potential runtime errors
   - Null/undefined checks

2. **Security Issues**
   - Input validation gaps
   - Injection vulnerabilities
   - Authentication/authorization flaws
   - Sensitive data exposure

3. **Code Quality**
   - Code duplication
   - Complex functions needing refactoring
   - Missing error handling
   - Inconsistent naming conventions

4. **Best Practices**
   - Language-specific conventions
   - Design pattern usage
   - Separation of concerns
   - Test coverage gaps

**Output Format:**
Return a JSON object with this exact structure:

```json
{{
  "summary": "Overall assessment (2-3 sentences)",
  "quality_score": 75,  // 0-100 score
  "issues": [
    {{
      "severity": "critical|high|medium|low",
      "category": "bug|security|quality|best_practice",
      "file": "path/to/file.py",
      "line": 42,
      "title": "Short issue title",
      "description": "Detailed description of the issue",
      "recommendation": "How to fix it"
    }}
  ],
  "strengths": [
    "What was done well"
  ],
  "recommendations": [
    "Top priority improvements"
  ]
}}
```

**Severity Guidelines:**
- **critical**: Security vulnerability or guaranteed crash
- **high**: Major bug affecting core functionality
- **medium**: Code quality issue or edge case bug
- **low**: Style/best practice suggestion

Be thorough but fair. Acknowledge what was done well while identifying real issues."""


class CodeReviewerAgent(BaseAgent):
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            model = os.environ.get("QWEN_MODEL", "qwen-coder-plus")
            config = AgentConfig(
                name="qwen",
                role="reviewer",
                command="qwen",
                subcommand=None,
                args=["--model", model] if model else [],
                timeout_seconds=600,  # 10 minutes for thorough review
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

    def build_prompt(
        self,
        project_name: str,
        original_request: str,
        files: list[dict]
    ) -> str:
        """Build code review prompt from project files."""
        file_contents = []
        
        for file_info in files:
            path = file_info.get("path", "unknown")
            content = file_info.get("content", "")
            
            # Truncate very long files but keep them reviewable
            if len(content) > 5000:
                content = content[:2500] + "\n... [truncated] ...\n" + content[-2500:]
            
            file_contents.append(f"### File: {path}\n\n```{self._get_language(path)}\n{content}\n```")
        
        return CODE_REVIEW_PROMPT_TEMPLATE.format(
            project_name=project_name,
            original_request=original_request,
            file_contents="\n\n".join(file_contents),
        )

    def _get_language(self, filepath: str) -> str:
        """Get language hint from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sql": "sql",
            ".sh": "bash",
            ".md": "markdown",
        }
        for ext, lang in ext_map.items():
            if filepath.endswith(ext):
                return lang
        return "text"

    def parse_output(self, raw_output: str) -> Any:
        """Parse code review JSON output."""
        from parsing.extractor import extract_json
        return extract_json(raw_output)
