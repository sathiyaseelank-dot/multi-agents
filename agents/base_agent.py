"""Abstract base class for all agent integrations."""

import asyncio
import logging
import os
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from parsing.sanitizer import clean_output

logger = logging.getLogger(__name__)


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
