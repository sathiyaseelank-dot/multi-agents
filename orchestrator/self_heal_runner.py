"""Self-healing runner for the Multi-Agent Orchestrator.

Wraps project execution with automatic error detection, reporting to Kilo AI,
and retry logic. When any error occurs during orchestration, validation, or
runtime execution, this module:
  1. Captures the error with full context
  2. Sends it to Kilo for analysis and repair
  3. Applies the fix to the project files
  4. Re-runs the failed phase
  5. Repeats up to max_repair_attempts before giving up
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .events import EventEmitter, EventType
from .repair_engine import (
    build_repair_prompt,
    classify_error,
    collect_relevant_files,
)
from .state_machine import State
from .project_builder import build_project
from .validation_engine import validate_project
from .runtime_executor import execute_project
from .dependency_resolver import resolve_dependencies

logger = logging.getLogger(__name__)

KILO_COMMAND = "kilo"
MAX_DEFAULT_REPAIRS = 5


class HealResult:
    """Result of a self-healing cycle."""

    def __init__(self):
        self.success: bool = False
        self.total_attempts: int = 0
        self.repairs_applied: list[dict] = []
        self.errors_seen: list[dict] = []
        self.final_error: Optional[str] = None
        self.session_log: list[dict] = []

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_attempts": self.total_attempts,
            "repairs_applied": self.repairs_applied,
            "errors_seen": self.errors_seen,
            "final_error": self.final_error,
            "session_log": self.session_log,
        }


class SelfHealRunner:
    """Wraps orchestrator execution with automatic error recovery via Kilo."""

    def __init__(
        self,
        max_repair_attempts: int = MAX_DEFAULT_REPAIRS,
        memory_dir: str = "memory",
        log_dir: str = "logs",
        events: Optional[EventEmitter] = None,
    ):
        self.max_repair_attempts = max_repair_attempts
        self.memory_dir = Path(memory_dir)
        self.log_dir = Path(log_dir)
        self.events = events
        self._heal_log_path = self.memory_dir / "self-heal-log.json"
        self._kilo_available: Optional[bool] = None

    def is_kilo_available(self) -> bool:
        """Check if the kilo CLI is installed."""
        if self._kilo_available is None:
            self._kilo_available = shutil.which(KILO_COMMAND) is not None
        return self._kilo_available

    def _emit(self, event_type: EventType, data: dict) -> None:
        if self.events:
            self.events.emit(event_type, data)
        logger.info(
            "[SelfHeal] %s: %s", event_type.value, json.dumps(data, default=str)[:500]
        )

    async def heal_and_run(
        self,
        task_description: str,
        orchestrator_factory: Any = None,
    ) -> dict:
        """Run the orchestrator with self-healing. Re-runs on failure.

        Args:
            task_description: The task to execute.
            orchestrator_factory: A callable that returns an Orchestrator instance.
                If None, imports and creates one internally.

        Returns:
            Final orchestrator result dict with heal metadata attached.
        """
        if not self.is_kilo_available():
            logger.warning(
                "Kilo CLI not found — self-healing disabled, running normally"
            )
            return await self._run_without_heal(task_description, orchestrator_factory)

        heal_result = HealResult()
        attempt = 0

        while attempt <= self.max_repair_attempts:
            attempt += 1
            heal_result.total_attempts = attempt

            self._emit(
                EventType.INFO,
                {
                    "message": f"[SelfHeal] Attempt {attempt}/{self.max_repair_attempts + 1}"
                },
            )

            # Run orchestrator
            try:
                result = await self._run_orchestrator(
                    task_description, orchestrator_factory
                )
            except Exception as exc:
                error_info = {
                    "phase": "orchestration",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "attempt": attempt,
                }
                heal_result.errors_seen.append(error_info)
                self._emit(
                    EventType.ERROR,
                    {"message": f"[SelfHeal] Orchestration crashed: {exc}"},
                )

                if attempt <= self.max_repair_attempts:
                    repaired = await self._heal_error(
                        error_info=error_info,
                        project_dir=self._get_latest_project_dir(),
                        attempt=attempt,
                        heal_result=heal_result,
                    )
                    if repaired:
                        continue
                heal_result.final_error = str(exc)
                break

            # Check result status
            status = result.get("status", "unknown")
            if status == "completed":
                # Check if validation or runtime had issues
                val_ok = result.get("validation_result", {}).get("success", True)
                run_ok = result.get("runtime_result", {}).get("success", True)

                if val_ok and run_ok:
                    heal_result.success = True
                    self._emit(
                        EventType.INFO,
                        {"message": "[SelfHeal] Project completed successfully"},
                    )
                    break

                # Partial success — try to fix remaining issues
                error_info = self._extract_remaining_errors(result, attempt)
                if error_info and attempt <= self.max_repair_attempts:
                    heal_result.errors_seen.append(error_info)
                    repaired = await self._heal_error(
                        error_info=error_info,
                        project_dir=result.get("project_dir", ""),
                        attempt=attempt,
                        heal_result=heal_result,
                    )
                    if repaired:
                        continue

                heal_result.success = val_ok and run_ok
                break

            elif status == "failed":
                error_msg = result.get("error", "Unknown failure")
                error_info = {
                    "phase": "result",
                    "error": error_msg,
                    "attempt": attempt,
                }
                heal_result.errors_seen.append(error_info)
                self._emit(
                    EventType.ERROR,
                    {"message": f"[SelfHeal] Run failed: {error_msg}"},
                )

                if attempt <= self.max_repair_attempts:
                    repaired = await self._heal_error(
                        error_info=error_info,
                        project_dir=result.get("project_dir", ""),
                        attempt=attempt,
                        heal_result=heal_result,
                    )
                    if repaired:
                        continue

                heal_result.final_error = error_msg
                break
            else:
                heal_result.final_error = f"Unexpected status: {status}"
                break

        # Attach heal metadata to result
        result["_self_heal"] = heal_result.to_dict()
        self._persist_heal_log(heal_result)
        return result

    async def _run_without_heal(
        self, task_description: str, orchestrator_factory: Any
    ) -> dict:
        """Fall back to normal execution when Kilo is unavailable."""
        result = await self._run_orchestrator(task_description, orchestrator_factory)
        result["_self_heal"] = {"enabled": False, "reason": "kilo_cli_not_found"}
        return result

    async def _run_orchestrator(
        self, task_description: str, orchestrator_factory: Any
    ) -> dict:
        """Create and run the orchestrator."""
        if orchestrator_factory:
            orchestrator = orchestrator_factory()
        else:
            from .orchestrator import Orchestrator

            orchestrator = Orchestrator(
                memory_dir=str(self.memory_dir),
                log_dir=str(self.log_dir),
                events=self.events,
            )
        return await orchestrator.run(task_description)

    def _get_latest_project_dir(self) -> str:
        """Find the most recent project directory."""
        project_root = Path("project")
        if not project_root.exists():
            return ""
        dirs = sorted(project_root.iterdir(), reverse=True)
        for d in dirs:
            if d.is_dir():
                return str(d)
        return ""

    def _extract_remaining_errors(self, result: dict, attempt: int) -> Optional[dict]:
        """Extract actionable errors from a completed-but-broken result."""
        validation = result.get("validation_result", {})
        if not validation.get("success", True) and validation.get("errors"):
            first_error = validation["errors"][0]
            return {
                "phase": "validation",
                "error": first_error.get("message", "Validation error"),
                "file_path": first_error.get("path"),
                "error_type": first_error.get("kind", "unknown"),
                "attempt": attempt,
            }

        runtime = result.get("runtime_result", {})
        if not runtime.get("success", True) and runtime.get("errors"):
            return {
                "phase": "runtime",
                "error": "\n".join(runtime["errors"][:5]),
                "file_path": self._infer_file_from_runtime(runtime),
                "attempt": attempt,
            }

        return None

    def _infer_file_from_runtime(self, runtime: dict) -> Optional[str]:
        entrypoint = runtime.get("entrypoint")
        if entrypoint:
            try:
                return str(Path(entrypoint).relative_to(Path.cwd()))
            except ValueError:
                return entrypoint
        return None

    async def _heal_error(
        self,
        error_info: dict,
        project_dir: str,
        attempt: int,
        heal_result: HealResult,
    ) -> bool:
        """Send error to Kilo for repair. Returns True if repair was applied.

        Args:
            error_info: Dict with phase, error, file_path, etc.
            project_dir: Path to the project directory.
            attempt: Current attempt number.
            heal_result: The HealResult to update.

        Returns:
            True if a repair was successfully applied.
        """
        if not project_dir or not Path(project_dir).exists():
            project_dir = self._get_latest_project_dir()
        if not project_dir:
            self._emit(
                EventType.WARNING,
                {"message": "[SelfHeal] No project directory found for repair"},
            )
            return False

        error_message = error_info.get("error", "Unknown error")
        phase = error_info.get("phase", "unknown")
        file_path = error_info.get("file_path")
        error_type = classify_error(error_message, phase=phase)

        self._emit(
            EventType.INFO,
            {
                "message": f"[SelfHeal] Sending to Kilo for repair (attempt {attempt}, "
                f"type={error_type}, phase={phase})"
            },
        )

        # Collect relevant files for context
        relevant_files = collect_relevant_files(
            project_dir,
            file_path=file_path,
            limit=5,
        )

        expected_behaviors = {
            "validation": "The project should validate cleanly with no syntax, import, or structural errors.",
            "runtime": "The project should start successfully and serve requests without crashing.",
            "orchestration": "The orchestrator should complete without unhandled exceptions.",
            "result": "The project should complete all phases without fatal errors.",
        }

        prompt = build_repair_prompt(
            project_dir=project_dir,
            error_message=error_message,
            error_type=error_type,
            relevant_files=relevant_files,
            expected_behavior=expected_behaviors.get(
                phase, expected_behaviors["result"]
            ),
            target_file=file_path,
        )

        # Call Kilo CLI
        repair_result = await self._call_kilo(prompt)

        if not repair_result:
            self._emit(
                EventType.WARNING,
                {"message": "[SelfHeal] Kilo returned no repair"},
            )
            return False

        # Apply repair
        files_applied = self._apply_repair(project_dir, repair_result)

        if not files_applied:
            return False

        repair_record = {
            "attempt": attempt,
            "phase": phase,
            "error_type": error_type,
            "error": error_message[:500],
            "files_applied": files_applied,
            "summary": repair_result.get("summary", ""),
            "timestamp": datetime.now().isoformat(),
        }
        heal_result.repairs_applied.append(repair_record)

        self._emit(
            EventType.INFO,
            {
                "message": f"[SelfHeal] Repair applied: {repair_result.get('summary', 'files updated')}",
            },
        )
        return True

    async def _call_kilo(self, prompt: str) -> Optional[dict]:
        """Execute the Kilo CLI with a repair prompt and parse the output."""
        cmd = [KILO_COMMAND, "run", prompt]
        logger.info("Calling Kilo: %s (prompt length: %d)", cmd[0], len(prompt))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        except asyncio.TimeoutError:
            logger.error("Kilo repair call timed out")
            return None
        except Exception as exc:
            logger.error("Kilo repair call failed: %s", exc)
            return None

        raw_output = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            logger.warning(
                "Kilo exited with code %d: %s", proc.returncode, stderr_text[:300]
            )
            # Still try to parse output in case partial results were returned

        return self._parse_kilo_repair_output(raw_output)

    def _parse_kilo_repair_output(self, raw_output: str) -> Optional[dict]:
        """Parse Kilo CLI output into a repair manifest."""
        from parsing.extractor import extract_json, extract_code_blocks

        # Try JSON extraction first
        json_result = extract_json(raw_output)
        if isinstance(json_result, dict) and json_result.get("files"):
            return json_result

        # Try code block extraction
        blocks = extract_code_blocks(raw_output)
        if blocks:
            files = []
            for index, block in enumerate(blocks, 1):
                code = block.get("code", "")
                if not code.strip():
                    continue
                lang = block.get("language", "text")
                path = self._guess_file_path(lang, index)
                files.append(
                    {
                        "path": path,
                        "content": code,
                        "operation": "update",
                    }
                )
            if files:
                return {
                    "files": files,
                    "summary": f"Kilo repaired {len(files)} file(s)",
                    "errors": [],
                }

        return None

    def _guess_file_path(self, language: str, index: int) -> str:
        ext_map = {
            "python": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "jsx": ".jsx",
            "html": ".html",
            "css": ".css",
        }
        ext = ext_map.get(language.lower(), ".txt")
        if language.lower() in ("python", "py"):
            return f"backend/generated_fix_{index}.py"
        if language.lower() in ("javascript", "js", "jsx", "typescript", "ts"):
            return f"frontend/generated_fix_{index}{ext}"
        return f"generated_fix_{index}{ext}"

    def _apply_repair(self, project_dir: str, repair_result: dict) -> list[str]:
        """Apply repaired files to the project directory."""
        applied = []
        project_path = Path(project_dir)

        for file_info in repair_result.get("files", []):
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")
            operation = file_info.get("operation", "update")

            if not file_path or not content.strip():
                continue

            target = project_path / file_path
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                target.write_text(content)
                applied.append(file_path)
                logger.info("Applied repair to %s", target)
            except Exception as exc:
                logger.error("Failed to write repair to %s: %s", target, exc)

        return applied

    def _persist_heal_log(self, heal_result: HealResult) -> None:
        """Append healing results to the persistent log."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        existing = []
        if self._heal_log_path.exists():
            try:
                existing = json.loads(self._heal_log_path.read_text())
                if not isinstance(existing, list):
                    existing = [existing]
            except (json.JSONDecodeError, OSError):
                existing = []

        entry = {
            "timestamp": datetime.now().isoformat(),
            **heal_result.to_dict(),
        }
        existing.append(entry)

        try:
            self._heal_log_path.write_text(json.dumps(existing, indent=2, default=str))
        except OSError as exc:
            logger.error("Failed to persist heal log: %s", exc)

    # ------------------------------------------------------------------
    # Standalone healing methods (for use outside the orchestrator)
    # ------------------------------------------------------------------

    async def heal_project(
        self,
        project_dir: str,
        phase: str = "runtime",
    ) -> dict:
        """Heal an existing project directory by validating, running, and
        sending errors to Kilo.

        Args:
            project_dir: Path to the project to heal.
            phase: Which phase to heal ("validation", "runtime", "both").

        Returns:
            Dict with healing results.
        """
        if not self.is_kilo_available():
            return {"success": False, "error": "Kilo CLI not available"}

        project_path = Path(project_dir)
        if not project_path.exists():
            return {
                "success": False,
                "error": f"Project directory not found: {project_dir}",
            }

        heal_result = HealResult()
        attempt = 0

        while attempt < self.max_repair_attempts:
            attempt += 1
            heal_result.total_attempts = attempt

            self._emit(
                EventType.INFO,
                {
                    "message": f"[SelfHeal] Heal attempt {attempt}/{self.max_repair_attempts}"
                },
            )

            # Resolve dependencies first
            resolve_dependencies(project_dir)

            # Validate
            if phase in ("validation", "both"):
                val_result = validate_project(project_dir)
                if not val_result.get("success"):
                    errors = val_result.get("errors", [])
                    error_info = {
                        "phase": "validation",
                        "error": errors[0].get("message", "Validation error")
                        if errors
                        else "Unknown",
                        "file_path": errors[0].get("path") if errors else None,
                        "attempt": attempt,
                    }
                    heal_result.errors_seen.append(error_info)

                    repaired = await self._heal_error(
                        error_info=error_info,
                        project_dir=project_dir,
                        attempt=attempt,
                        heal_result=heal_result,
                    )
                    if repaired:
                        continue
                    heal_result.final_error = error_info["error"]
                    break

            # Runtime
            if phase in ("runtime", "both"):
                run_result = execute_project(project_dir)
                if not run_result.get("success"):
                    errors = run_result.get("errors", [])
                    error_info = {
                        "phase": "runtime",
                        "error": "\n".join(errors[:5]) if errors else "Runtime error",
                        "file_path": run_result.get("entrypoint"),
                        "attempt": attempt,
                    }
                    heal_result.errors_seen.append(error_info)

                    repaired = await self._heal_error(
                        error_info=error_info,
                        project_dir=project_dir,
                        attempt=attempt,
                        heal_result=heal_result,
                    )
                    if repaired:
                        continue
                    heal_result.final_error = error_info["error"]
                    break

            # All passed
            heal_result.success = True
            self._emit(
                EventType.INFO,
                {"message": "[SelfHeal] Project healed successfully"},
            )
            break

        self._persist_heal_log(heal_result)
        return heal_result.to_dict()


# ------------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------------


async def self_heal_run(
    task_description: str,
    max_repair_attempts: int = MAX_DEFAULT_REPAIRS,
    memory_dir: str = "memory",
    log_dir: str = "logs",
) -> dict:
    """One-call self-healing orchestrator run.

    Usage:
        result = await self_heal_run("Build a REST API with auth")
    """
    runner = SelfHealRunner(
        max_repair_attempts=max_repair_attempts,
        memory_dir=memory_dir,
        log_dir=log_dir,
    )
    return await runner.heal_and_run(task_description)
