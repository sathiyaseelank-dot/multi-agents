"""Orchestration healer — monitors the orchestrator subprocess and heals hangs.

Runs the orchestrator as a monitored subprocess.  When the process produces no
output for ``health_timeout`` seconds, the ``HealthMonitor`` flags it as stuck
and ``OrchestrationHealer`` applies a two-phase repair strategy:

1. **Config fix** — adjust ``config/agents.yaml`` timeouts/retries, then restart.
2. **Code fix** — send relevant orchestrator source files to a repair AI
   (Kilo → OpenCode → Gemini fallback chain) for patching, then restart.

The healer is the *parent* process; it never shares memory with the orchestrator.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from .events import EventEmitter, EventType

logger = logging.getLogger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_HEALTH_TIMEOUT = 60  # seconds with no output before "stuck"
DEFAULT_MAX_HEALS = 3
REPAIR_AGENTS = ["kilo", "opencode", "gemini"]
LOG_PREFIX = "[OrchHeal]"

# Files relevant to specific orchestrator phases (for targeted code repair)
PHASE_FILE_MAP: dict[str, list[str]] = {
    "EXECUTING": [
        "orchestrator/runtime_executor.py",
        "orchestrator/task_router.py",
        "orchestrator/orchestrator.py",
    ],
    "PLANNING": [
        "orchestrator/orchestrator.py",
        "orchestrator/goal_analyzer.py",
    ],
    "BUILDING": [
        "orchestrator/project_builder.py",
        "orchestrator/orchestrator.py",
    ],
    "VALIDATING": [
        "orchestrator/validation_engine.py",
        "orchestrator/orchestrator.py",
    ],
    "RUNNING": [
        "orchestrator/runtime_executor.py",
        "orchestrator/orchestrator.py",
    ],
    "PRE_VALIDATING": [
        "orchestrator/pre_validation.py",
        "orchestrator/orchestrator.py",
    ],
    "REPLANNING": [
        "orchestrator/orchestrator.py",
        "orchestrator/task_manager.py",
    ],
}

# ── State transition regex ──────────────────────────────────────────────────
_STATE_TRANSITION_RE = re.compile(r"State:\s+(\w+)\s*->\s*(\w+)")
_PHASE_RE = re.compile(r"\[Phase\s+(\d+)/(\d+)\]")


class HealthStatus:
    """Snapshot of subprocess health."""

    def __init__(self) -> None:
        self.last_output_time: float = time.monotonic()
        self.current_phase: str = "INIT"
        self.total_lines: int = 0
        self.output_lines: list[str] = []

    @property
    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_output_time

    def record_line(self, line: str) -> None:
        self.last_output_time = time.monotonic()
        self.total_lines += 1
        self.output_lines.append(line)
        if len(self.output_lines) > 500:
            self.output_lines = self.output_lines[-500:]

        # Detect state transitions
        m = _STATE_TRANSITION_RE.search(line)
        if m:
            self.current_phase = m.group(2)

        # Detect phase messages
        pm = _PHASE_RE.search(line)
        if pm:
            self.current_phase = "EXECUTING"


class HealthMonitor:
    """Reads orchestrator subprocess output and detects hangs.

    Works with ``asyncio`` — call ``start()`` to begin monitoring, ``stop()``
    to cancel.  Use ``is_stuck`` to check hang status.
    """

    def __init__(
        self,
        proc: asyncio.subprocess.Process,
        health_timeout: float = DEFAULT_HEALTH_TIMEOUT,
    ) -> None:
        self._proc = proc
        self._timeout = health_timeout
        self.status = HealthStatus()
        self._tasks: list[asyncio.Task] = []
        self._stuck = False
        self._stopped = False

    @property
    def is_stuck(self) -> bool:
        return self._stuck

    @property
    def stopped(self) -> bool:
        return self._stopped

    def start(self) -> None:
        """Begin reading stdout/stderr in background tasks."""
        if self._proc.stdout:
            self._tasks.append(
                asyncio.ensure_future(self._read_stream(self._proc.stdout, "stdout"))
            )
        if self._proc.stderr:
            self._tasks.append(
                asyncio.ensure_future(self._read_stream(self._proc.stderr, "stderr"))
            )
        self._tasks.append(asyncio.ensure_future(self._watchdog()))

    async def stop(self) -> None:
        """Cancel all monitoring tasks."""
        self._stopped = True
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _read_stream(self, stream: asyncio.StreamReader, name: str) -> None:
        """Read lines from a stream until EOF or cancellation."""
        try:
            while not self._stopped:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                if line:
                    logger.debug("%s %s: %s", LOG_PREFIX, name, line)
                    self.status.record_line(line)
        except asyncio.CancelledError:
            pass

    async def _watchdog(self) -> None:
        """Periodically check if the process has been idle too long."""
        try:
            while not self._stopped:
                await asyncio.sleep(min(self._timeout / 3, 10))
                if self._proc.returncode is not None:
                    break
                if self.status.idle_seconds >= self._timeout:
                    self._stuck = True
                    break
        except asyncio.CancelledError:
            pass


class OrchestrationHealer:
    """Spawn the orchestrator as a subprocess, monitor health, and heal hangs.

    Usage::

        healer = OrchestrationHealer(task="Build a REST API")
        result = await healer.run()
    """

    def __init__(
        self,
        task: str,
        health_timeout: float = DEFAULT_HEALTH_TIMEOUT,
        max_heals: int = DEFAULT_MAX_HEALS,
        log_dir: str = "logs",
        memory_dir: str = "memory",
        output_dir: str = "output",
        config_path: str = "config/agents.yaml",
        orchestrator_module: str = "orchestrator.main",
        events: Optional[EventEmitter] = None,
    ) -> None:
        self.task = task
        self.health_timeout = health_timeout
        self.max_heals = max_heals
        self.log_dir = log_dir
        self.memory_dir = memory_dir
        self.output_dir = output_dir
        self.config_path = Path(config_path)
        self.orchestrator_module = orchestrator_module
        self.events = events

        self._heal_count = 0
        self._restart_count = 0
        self._max_restarts = max_heals + 2
        self._heal_log: list[dict] = []
        self._project_root = Path(__file__).resolve().parent.parent

    # ── Public API ────────────────────────────────────────────────────────

    async def run(self) -> dict:
        """Run the orchestrator with health monitoring and healing.

        Returns a result dict with ``status``, ``returncode``, and heal metadata.
        """
        while self._restart_count <= self._max_restarts:
            self._restart_count += 1
            result = await self._run_once()
            status = result.get("status")

            if status == "completed":
                result["_orch_heal"] = self._build_heal_meta()
                return result

            if status == "stuck":
                if self._heal_count >= self.max_heals:
                    logger.error(
                        "%s Max heals (%d) exhausted", LOG_PREFIX, self.max_heals
                    )
                    result["_orch_heal"] = self._build_heal_meta()
                    return result

                healed = await self._attempt_heal(result)
                if not healed:
                    result["_orch_heal"] = self._build_heal_meta()
                    return result
                # Loop will restart
                continue

            # Process exited normally but with failure — no heal possible
            result["_orch_heal"] = self._build_heal_meta()
            return result

        return {
            "status": "failed",
            "error": f"Max restarts ({self._max_restarts}) exceeded",
            "_orch_heal": self._build_heal_meta(),
        }

    # ── Subprocess management ─────────────────────────────────────────────

    async def _run_once(self) -> dict:
        """Run the orchestrator subprocess once with health monitoring."""
        cmd = self._build_command()
        logger.info(
            "%s Starting orchestrator (restart #%d): %s",
            LOG_PREFIX,
            self._restart_count,
            " ".join(cmd),
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._project_root),
            )
        except Exception as exc:
            logger.error("%s Failed to start orchestrator: %s", LOG_PREFIX, exc)
            return {"status": "failed", "error": str(exc), "returncode": -1}

        monitor = HealthMonitor(proc, health_timeout=self.health_timeout)
        monitor.start()

        try:
            # Wait for process to finish or get stuck
            while proc.returncode is None:
                if monitor.is_stuck:
                    logger.warning(
                        "%s Orchestrator stuck (idle %.0fs in phase %s)",
                        LOG_PREFIX,
                        monitor.status.idle_seconds,
                        monitor.status.current_phase,
                    )
                    self._emit(
                        EventType.ORCHESTRATION_STUCK,
                        {
                            "phase": monitor.status.current_phase,
                            "idle_seconds": monitor.status.idle_seconds,
                            "restart_count": self._restart_count,
                        },
                    )
                    await monitor.stop()
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=10)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                    return {
                        "status": "stuck",
                        "phase": monitor.status.current_phase,
                        "idle_seconds": monitor.status.idle_seconds,
                        "last_lines": monitor.status.output_lines[-20:],
                        "returncode": proc.returncode,
                    }
                await asyncio.sleep(1)

            await monitor.stop()
            rc = proc.returncode
            if rc == 0:
                return {
                    "status": "completed",
                    "returncode": rc,
                    "output_lines": monitor.status.total_lines,
                }
            return {
                "status": "failed",
                "returncode": rc,
                "error": f"Orchestrator exited with code {rc}",
                "last_lines": monitor.status.output_lines[-20:],
            }
        except Exception as exc:
            await monitor.stop()
            logger.error("%s Error monitoring orchestrator: %s", LOG_PREFIX, exc)
            return {"status": "failed", "error": str(exc), "returncode": -1}

    def _build_command(self) -> list[str]:
        """Build the CLI command to launch the orchestrator."""
        cmd = [
            "python",
            "-m",
            self.orchestrator_module,
            self.task,
            "--log-dir",
            self.log_dir,
            "--memory-dir",
            self.memory_dir,
        ]
        return cmd

    # ── Healing ───────────────────────────────────────────────────────────

    async def _attempt_heal(self, stuck_result: dict) -> bool:
        """Apply a two-phase heal.  Returns True if a fix was applied."""
        self._heal_count += 1
        phase = stuck_result.get("phase", "unknown")

        # Phase 1: config fix
        config_applied = self._try_config_fix(phase)
        if config_applied:
            return True

        # Phase 2: code fix via AI
        code_applied = await self._try_code_fix(phase, stuck_result)
        if code_applied:
            return True

        self._emit(
            EventType.ORCHESTRATION_HEAL_FAILED,
            {
                "reason": "Both config and code fixes failed",
                "phase": phase,
                "attempt": self._heal_count,
            },
        )
        return False

    # ── Config fix ────────────────────────────────────────────────────────

    def _try_config_fix(self, phase: str) -> bool:
        """Attempt to fix by adjusting agent config timeouts/retries."""
        if not self.config_path.exists():
            logger.warning("%s Config file not found: %s", LOG_PREFIX, self.config_path)
            return False

        try:
            raw = self.config_path.read_text()
            data = yaml.safe_load(raw)
        except Exception as exc:
            logger.warning("%s Failed to read config: %s", LOG_PREFIX, exc)
            return False

        if not isinstance(data, dict) or "agents" not in data:
            return False

        agents = data["agents"]
        changed = False

        for agent_cfg in agents.values():
            if not isinstance(agent_cfg, dict):
                continue
            old_timeout = agent_cfg.get("timeout_seconds", 0)
            old_retries = agent_cfg.get("retry_count", 0)

            if old_timeout < 300:
                agent_cfg["timeout_seconds"] = min(old_timeout * 2, 600)
                changed = True
            if old_retries < 5:
                agent_cfg["retry_count"] = min(old_retries + 1, 5)
                changed = True

        if not changed:
            return False

        # Backup
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = self.config_path.with_suffix(f".yaml.bak.{ts}")
        shutil.copy2(self.config_path, backup)
        logger.info("%s Config backed up to %s", LOG_PREFIX, backup)

        # Validate before writing
        try:
            new_yaml = yaml.dump(data, default_flow_style=False)
            yaml.safe_load(new_yaml)  # roundtrip validation
        except Exception as exc:
            logger.warning("%s Generated YAML invalid, skipping: %s", LOG_PREFIX, exc)
            return False

        self.config_path.write_text(new_yaml)
        logger.info("%s Config updated (timeouts doubled, retries+1)", LOG_PREFIX)

        self._emit(
            EventType.ORCHESTRATION_HEAL_APPLIED,
            {
                "heal_type": "config",
                "summary": "Increased agent timeouts/retries in agents.yaml",
                "phase": phase,
                "attempt": self._heal_count,
            },
        )

        self._log_heal("config", phase, True)
        return True

    # ── Code fix ──────────────────────────────────────────────────────────

    async def _try_code_fix(self, phase: str, stuck_result: dict) -> bool:
        """Attempt to fix by sending orchestrator source to a repair AI."""
        relevant_files = self._collect_orch_files(phase)
        if not relevant_files:
            return False

        error_message = (
            f"Orchestrator stuck in phase {phase} — "
            f"idle for {stuck_result.get('idle_seconds', '?')}s with no output."
        )
        last_lines = stuck_result.get("last_lines", [])
        if last_lines:
            error_message += "\nLast output lines:\n" + "\n".join(last_lines[-10:])

        prompt = self._build_code_fix_prompt(phase, error_message, relevant_files)

        for agent in REPAIR_AGENTS:
            self._emit(
                EventType.ORCHESTRATION_HEAL_STARTED,
                {
                    "heal_type": "code",
                    "attempt": self._heal_count,
                    "max_attempts": self.max_heals,
                    "agent": agent,
                    "phase": phase,
                },
            )

            repair_result = await self._call_repair_agent(agent, prompt)
            if repair_result:
                applied = self._apply_code_fix(repair_result)
                if applied:
                    self._emit(
                        EventType.ORCHESTRATION_HEAL_APPLIED,
                        {
                            "heal_type": "code",
                            "summary": repair_result.get(
                                "summary", f"Repaired {len(applied)} file(s)"
                            ),
                            "agent": agent,
                            "phase": phase,
                            "attempt": self._heal_count,
                            "files": applied,
                        },
                    )
                    self._log_heal("code", phase, True, agent=agent, files=applied)
                    return True

            logger.warning("%s Agent %s returned no repair", LOG_PREFIX, agent)

        self._log_heal("code", phase, False)
        return False

    def _collect_orch_files(self, phase: str) -> list[dict]:
        """Collect orchestrator source files relevant to the stuck phase."""
        file_paths = PHASE_FILE_MAP.get(phase, ["orchestrator/orchestrator.py"])
        selected = []
        for rel_path in file_paths:
            full = self._project_root / rel_path
            if full.exists():
                selected.append(
                    {"path": rel_path, "content": full.read_text(errors="replace")}
                )
        # Always include state_machine.py for context
        sm = self._project_root / "orchestrator" / "state_machine.py"
        if sm.exists() and not any(
            f["path"] == "orchestrator/state_machine.py" for f in selected
        ):
            selected.append(
                {
                    "path": "orchestrator/state_machine.py",
                    "content": sm.read_text(errors="replace"),
                }
            )
        return selected

    def _build_code_fix_prompt(
        self,
        phase: str,
        error_message: str,
        relevant_files: list[dict],
    ) -> str:
        """Build a repair prompt for the AI agent."""
        file_sections = []
        for item in relevant_files:
            file_sections.append(
                f"File: {item['path']}\n```python\n{item['content']}\n```"
            )

        return (
            "You are fixing a hang/stuck issue in a Python multi-agent orchestrator.\n"
            f"The orchestrator got stuck in phase: {phase}\n"
            f"Error context: {error_message}\n\n"
            "Relevant orchestrator source files:\n"
            f"{chr(10).join(file_sections)}\n\n"
            "The fix should ensure the orchestrator does not hang in this phase.\n"
            "Common causes: missing timeout handling, infinite loops, blocked subprocess calls,\n"
            "missing error handling, or deadlocks in async code.\n\n"
            "Return JSON only:\n"
            "{\n"
            '  "files": [\n'
            "    {\n"
            '      "path": "<relative file path>",\n'
            '      "content": "<full fixed file content>",\n'
            '      "operation": "update"\n'
            "    }\n"
            "  ],\n"
            '  "summary": "<short description of the fix>",\n'
            '  "errors": []\n'
            "}\n"
        )

    async def _call_repair_agent(self, agent: str, prompt: str) -> Optional[dict]:
        """Call a repair AI agent and parse its output."""
        cmd = self._build_agent_command(agent, prompt)
        if cmd is None:
            return None

        if not shutil.which(cmd[0]):
            logger.warning("%s Agent %s CLI not found", LOG_PREFIX, agent)
            return None

        logger.info(
            "%s Calling %s for repair (prompt: %d chars)",
            LOG_PREFIX,
            agent,
            len(prompt),
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._project_root),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        except asyncio.TimeoutError:
            logger.error("%s %s repair call timed out", LOG_PREFIX, agent)
            return None
        except Exception as exc:
            logger.error("%s %s repair call failed: %s", LOG_PREFIX, agent, exc)
            return None

        raw = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            logger.warning(
                "%s %s exited %d: %s",
                LOG_PREFIX,
                agent,
                proc.returncode,
                stderr_text[:300],
            )

        return self._parse_agent_output(raw)

    def _build_agent_command(self, agent: str, prompt: str) -> Optional[list[str]]:
        """Build CLI command for a repair agent."""
        if agent == "kilo":
            return ["kilo", "run", prompt]
        if agent == "opencode":
            return ["opencode", "run", prompt]
        if agent == "gemini":
            return ["gemini", "-p", prompt, "--output-format", "json"]
        return None

    def _parse_agent_output(self, raw_output: str) -> Optional[dict]:
        """Parse AI agent output into a repair manifest."""
        from parsing.extractor import extract_json, extract_code_blocks

        # Try JSON first
        json_result = extract_json(raw_output)
        if isinstance(json_result, dict) and json_result.get("files"):
            return json_result

        # Try code blocks
        blocks = extract_code_blocks(raw_output)
        if blocks:
            files = []
            for index, block in enumerate(blocks, 1):
                code = block.get("code", "")
                if not code.strip():
                    continue
                lang = block.get("language", "text")
                ext = {
                    "python": ".py",
                    "py": ".py",
                    "yaml": ".yaml",
                    "yml": ".yaml",
                }.get(lang.lower(), ".txt")
                path = f"orchestrator/generated_fix_{index}{ext}"
                files.append({"path": path, "content": code, "operation": "update"})
            if files:
                return {
                    "files": files,
                    "summary": f"Repaired {len(files)} file(s)",
                    "errors": [],
                }

        return None

    def _apply_code_fix(self, repair_result: dict) -> list[str]:
        """Apply repaired files to the project directory."""
        applied = []
        for file_info in repair_result.get("files", []):
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            operation = file_info.get("operation", "update")

            if not file_path or not content.strip():
                continue

            target = self._project_root / file_path

            # Only allow writing within orchestrator/ or config/
            try:
                target.resolve().relative_to(self._project_root)
            except ValueError:
                logger.warning(
                    "%s Refusing to write outside project: %s", LOG_PREFIX, target
                )
                continue

            # Only allow .py and .yaml files
            if target.suffix not in {".py", ".yaml", ".yml"}:
                logger.warning(
                    "%s Refusing to write non-code file: %s", LOG_PREFIX, target
                )
                continue

            if operation == "update":
                # Backup original
                if target.exists():
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    backup = target.with_suffix(target.suffix + f".bak.{ts}")
                    shutil.copy2(target, backup)

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                applied.append(file_path)
                logger.info("%s Applied fix to %s", LOG_PREFIX, target)

        return applied

    # ── Helpers ───────────────────────────────────────────────────────────

    def _emit(self, event_type: EventType, data: dict) -> None:
        if self.events:
            self.events.emit(event_type, data)
        logger.info(
            "%s %s: %s",
            LOG_PREFIX,
            event_type.value,
            json.dumps(data, default=str)[:500],
        )

    def _log_heal(
        self,
        heal_type: str,
        phase: str,
        success: bool,
        agent: str = "",
        files: list[str] | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "heal_type": heal_type,
            "phase": phase,
            "success": success,
            "attempt": self._heal_count,
            "restart_count": self._restart_count,
        }
        if agent:
            entry["agent"] = agent
        if files:
            entry["files"] = files
        self._heal_log.append(entry)

    def _build_heal_meta(self) -> dict:
        return {
            "enabled": True,
            "heal_count": self._heal_count,
            "restart_count": self._restart_count,
            "heals": self._heal_log,
        }
