"""Abstract base class for all agent integrations."""

import asyncio
import logging
import os
import re
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from parsing.extractor import extract_code_blocks, extract_json
from parsing.sanitizer import clean_output

logger = logging.getLogger(__name__)

LANG_TO_EXT = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "jsx": ".jsx",
    "tsx": ".tsx",
    "html": ".html",
    "css": ".css",
    "json": ".json",
    "yaml": ".yaml",
    "yml": ".yml",
    "sql": ".sql",
    "bash": ".sh",
    "sh": ".sh",
    "text": ".txt",
}


@dataclass
class AgentConfig:
    name: str
    role: str
    command: str
    subcommand: Optional[str] = None
    args: list[str] = field(default_factory=list)
    timeout_seconds: int = 120
    retry_count: int = 3
    retry_backoff_seconds: int = 2
    env_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent: str
    status: str  # "success", "error", "timeout"
    raw_output: str = ""
    parsed_output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0


def manifest_output_instructions(default_dir: str) -> str:
    return (
        "Return JSON only using this schema:\n"
        "{\n"
        '  "files": [\n'
        "    {\n"
        f'      "path": "{default_dir}/<filename>",\n'
        '      "content": "<full file content>",\n'
        '      "operation": "create"\n'
        "    }\n"
        "  ],\n"
        '  "summary": "<short summary>",\n'
        '  "errors": []\n'
        "}\n"
        "Do not wrap the JSON in markdown fences."
    )


def normalize_manifest_output(raw_output: str, task_type: str) -> Any:
    """Normalize worker output to the artifact manifest contract."""
    json_result = extract_json(raw_output)
    if isinstance(json_result, dict) and json_result.get("files"):
        files = []
        code_blocks = []
        for index, file_info in enumerate(json_result.get("files", []), 1):
            path = str(file_info.get("path", "")).strip()
            content = str(file_info.get("content", ""))
            if not path or not content.strip():
                continue
            operation = file_info.get("operation", "create")
            files.append({"path": path, "content": content, "operation": operation})
            code_blocks.append({
                "language": _language_from_path(path),
                "code": content,
                "path": path,
                "index": index,
            })

        if files:
            return {
                "files": files,
                "summary": json_result.get("summary", f"Generated {len(files)} file(s)"),
                "errors": list(json_result.get("errors", [])),
                "code_blocks": code_blocks,
                "files_created": [item["path"] for item in files],
            }

    blocks = extract_code_blocks(raw_output)
    if blocks:
        files = []
        for index, block in enumerate(blocks, 1):
            code = block.get("code", "")
            if not code.strip():
                continue
            path = _default_manifest_path(task_type, block.get("language", "text"), index)
            files.append({
                "path": path,
                "content": code,
                "operation": "create",
            })

        if files:
            return {
                "files": files,
                "summary": f"Generated {len(files)} file(s)",
                "errors": [],
                "code_blocks": [
                    {
                        "language": block.get("language", "text"),
                        "code": block.get("code", ""),
                        "path": files[index]["path"],
                        "index": index + 1,
                    }
                    for index, block in enumerate(blocks)
                    if block.get("code", "").strip()
                ],
                "files_created": [item["path"] for item in files],
            }

    cleaned = clean_output(raw_output)
    if cleaned:
        fallback_path = _default_manifest_path(task_type, "text", 1)
        return {
            "files": [{
                "path": fallback_path,
                "content": cleaned,
                "operation": "create",
            }],
            "summary": "Raw text output normalized into artifact manifest",
            "errors": [],
            "code_blocks": [],
            "files_created": [fallback_path],
            "raw_text": cleaned,
        }

    return None


def _default_manifest_path(task_type: str, language: str, index: int) -> str:
    base_dir = {
        "backend": "backend",
        "frontend": "frontend",
        "testing": "tests",
    }.get(task_type, "artifacts")
    ext = LANG_TO_EXT.get(language.lower(), ".txt")

    if task_type == "backend":
        filename = "generated.py" if index == 1 else f"generated_{index}.py"
    elif task_type == "frontend":
        filename = "App.jsx" if index == 1 and ext in {".js", ".jsx", ".tsx"} else f"generated_{index}{ext}"
    elif task_type == "testing":
        filename = "test_generated.py" if index == 1 else f"test_generated_{index}.py"
    else:
        filename = f"generated_{index}{ext}"
    return f"{base_dir}/{filename}"


def _language_from_path(path: str) -> str:
    suffix = os.path.splitext(path)[1].lower()
    for language, ext in LANG_TO_EXT.items():
        if ext == suffix:
            return language
    return re.sub(r"^\.", "", suffix) or "text"


class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"orchestrator.agent.{config.name}")

    def is_available(self) -> bool:
        """Check if the agent CLI tool is installed."""
        return shutil.which(self.config.command) is not None

    def build_command(self, prompt: str) -> list[str]:
        """Build the CLI command to execute."""
        cmd = [self.config.command]
        if self.config.subcommand:
            cmd.append(self.config.subcommand)
        cmd.extend(self.config.args)
        cmd.append(prompt)
        return cmd

    async def execute(self, prompt: str) -> AgentResult:
        """Run the agent with retry logic."""
        for attempt in range(self.config.retry_count):
            start = time.monotonic()
            try:
                result = await self._run(prompt)
                result.execution_time = time.monotonic() - start

                if result.status == "success":
                    return result

                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.config.retry_count} failed: {result.error}"
                )
            except asyncio.TimeoutError:
                elapsed = time.monotonic() - start
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.config.retry_count} timed out after {elapsed:.1f}s"
                )
                if attempt == self.config.retry_count - 1:
                    return AgentResult(
                        agent=self.config.name,
                        status="timeout",
                        error=f"Timed out after {self.config.timeout_seconds}s",
                        execution_time=elapsed,
                    )
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == self.config.retry_count - 1:
                    return AgentResult(
                        agent=self.config.name,
                        status="error",
                        error=str(e),
                        execution_time=time.monotonic() - start,
                    )

            if attempt < self.config.retry_count - 1:
                wait = self.config.retry_backoff_seconds * (2 ** attempt)
                self.logger.info(f"Retrying in {wait}s...")
                await asyncio.sleep(wait)

        return AgentResult(
            agent=self.config.name,
            status="error",
            error="All retry attempts exhausted",
        )

    async def _run(self, prompt: str) -> AgentResult:
        """Execute the CLI command as a subprocess."""
        cmd = self.build_command(prompt)
        # Log just the command, not the full prompt
        cmd_preview = f"{cmd[0]} {cmd[1] if len(cmd) > 1 else ''}"
        self.logger.info(f"Running: {cmd_preview} (prompt: {len(prompt)} chars)")

        env = os.environ.copy()
        env.update(self.config.env_vars)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        raw_output = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            return AgentResult(
                agent=self.config.name,
                status="error",
                raw_output=raw_output,
                error=f"Exit code {proc.returncode}: {stderr_text[:500]}",
            )

        parsed = self.parse_output(raw_output)
        return AgentResult(
            agent=self.config.name,
            status="success",
            raw_output=raw_output,
            parsed_output=parsed,
        )

    @abstractmethod
    def parse_output(self, raw_output: str) -> Any:
        """Parse the agent's raw output into structured data."""
        ...

    @abstractmethod
    def build_prompt(self, task_description: str, context: Optional[dict] = None) -> str:
        """Build the full prompt to send to the agent."""
        ...
