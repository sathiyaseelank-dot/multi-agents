"""Structured runtime events and console rendering for the orchestrator."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Callable, Deque

from __version__ import VERSION_DESCRIPTION


class EventType(StrEnum):
    """Standard orchestration events."""

    RUN_STARTED = "run_started"
    RUN_RESUMED = "run_resumed"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    PLAN_CREATED = "plan_created"
    PLAN_REVIEW_STARTED = "plan_review_started"
    PLAN_REVIEW_COMPLETED = "plan_review_completed"
    PLAN_REVISED = "plan_revised"
    PLAN_REJECTED = "plan_rejected"
    PLAN_APPROVED = "plan_approved"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_RETRY = "agent_retry"
    RUN_COMPLETED = "run_completed"
    PROJECT_BUILT = "project_built"


@dataclass(slots=True)
class Event:
    """Single structured runtime event."""

    type: str
    timestamp: str
    session_id: str
    data: dict


class EventEmitter:
    """Emit structured events and render human-friendly console output."""

    def __init__(
        self,
        session_id: str,
        summary_only: bool = False,
        max_history: int = 1000,
        writer: Callable[[str], None] | None = None,
    ):
        self.session_id = session_id
        self.summary_only = summary_only
        self._history: Deque[Event] = deque(maxlen=max_history)
        self._writer = writer or print

    def emit(self, event_type: EventType | str, data: dict | None = None) -> Event:
        """Create, store, and render a structured event."""
        normalized = EventType(event_type)
        event = Event(
            type=normalized.value,
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            data=data or {},
        )
        self._history.append(event)
        self._render(event)
        return event

    def get_history(self) -> list[dict]:
        """Return the emitted event history as serializable dictionaries."""
        return [asdict(event) for event in self._history]

    def _write(self, line: str = "") -> None:
        self._writer(line)

    def _render(self, event: Event) -> None:
        """Render a human-friendly message for a structured event."""
        event_type = EventType(event.type)
        data = event.data

        if self.summary_only and event_type in {
            EventType.TASK_STARTED,
            EventType.TASK_COMPLETED,
            EventType.AGENT_RETRY,
        }:
            return

        if event_type == EventType.RUN_STARTED:
            self._write()
            self._write("=" * 60)
            self._write(f"   {VERSION_DESCRIPTION}")
            self._write("   AI Development Team OS")
            self._write("=" * 60)
            self._write()
            self._write(f'  Task: "{data.get("task", "")}"')
            self._write()
            return

        if event_type == EventType.RUN_RESUMED:
            self._write()
            self._write("=" * 60)
            self._write(f"   {VERSION_DESCRIPTION}")
            self._write("   AI Development Team OS")
            self._write("=" * 60)
            self._write()
            self._write(f'  Resuming session: {data.get("session_id", self.session_id)}')
            self._write()
            self._write(
                f'  Checkpoint: {data.get("completed", 0)} completed, '
                f'{data.get("pending", 0)} pending'
            )
            self._write()
            if not self.summary_only:
                self._write("  Task status:")
                self._write("  " + "-" * 40)
                for task in data.get("tasks", []):
                    self._write(f'    [{task["icon"]}] {task["task_id"]}: {task["title"]}')
                self._write()
            return

        if event_type == EventType.INFO:
            self._write(f'  {data.get("message", "")}')
            return

        if event_type == EventType.WARNING:
            self._write(f'  [WARNING] {data.get("message", "")}')
            detail = data.get("detail")
            if detail:
                self._write(f"  {detail}")
            self._write()
            return

        if event_type == EventType.ERROR:
            self._write(f'  [ERROR] {data.get("message", "")}')
            return

        if event_type == EventType.PLAN_CREATED:
            plan = data.get("plan", {})
            tasks = plan.get("tasks", [])
            phases = plan.get("phases", [])
            self._write()
            self._write("=" * 60)
            self._write("  EXECUTION PLAN")
            self._write("=" * 60)

            if plan.get("epic"):
                self._write()
                self._write(f'  Epic: {plan["epic"]}')

            self._write()
            self._write(f"  Tasks ({len(tasks)}):")
            self._write("  " + "-" * 56)

            for task in tasks:
                deps = task.get("dependencies", [])
                dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
                self._write(f'    [{task.get("id", "?")}] {task.get("title", "Untitled")}')
                self._write(
                    f'           Agent: {task.get("agent", "?")} | '
                    f'Type: {task.get("type", "?")}{dep_str}'
                )

            if phases:
                self._write()
                self._write(f"  Phases ({len(phases)}):")
                self._write("  " + "-" * 56)
                for phase in phases:
                    parallel = "parallel" if phase.get("parallel") else "sequential"
                    self._write(
                        f'    Phase {phase.get("phase", "?")} ({parallel}): '
                        f'{phase.get("description", "")}'
                    )
                    self._write(f'           Tasks: {", ".join(phase.get("task_ids", []))}')

            execution_summary = data.get("execution_summary")
            if execution_summary:
                self._write()
                self._write(f'  Computed execution order ({data.get("phase_count", 0)} phases):')
                self._write(execution_summary)

            self._write()
            self._write("=" * 60)
            return

        if event_type == EventType.PLAN_REVIEW_STARTED:
            self._write(
                f'  [Review {data.get("iteration", "?")}] Reviewer analyzing plan'
            )
            return

        if event_type == EventType.PLAN_REVIEW_COMPLETED:
            approval = "APPROVED" if data.get("approval") else "REJECTED"
            self._write(
                f'  [Review {data.get("iteration", "?")}] {approval} '
                f'(confidence: {data.get("confidence", 0.0):.2f})'
            )
            return

        if event_type == EventType.PLAN_REVISED:
            self._write(
                f'  [Planner] Revised plan after review {data.get("iteration", "?")}'
            )
            return

        if event_type == EventType.PLAN_REJECTED:
            self._write(
                f'  [Planner] Debate ended without approval after '
                f'{data.get("review_iterations", 0)} review(s)'
            )
            return

        if event_type == EventType.PLAN_APPROVED:
            self._write(
                f'  [Planner] Plan approved after {data.get("review_iterations", 0)} review(s)'
            )
            return

        if event_type == EventType.PHASE_STARTED:
            self._write()
            self._write(
                f'  [Phase {data.get("phase")}/{data.get("total_phases")}] '
                f'[{data.get("mode", "").upper()}] {data.get("task_count", 0)} task(s): '
                f'{", ".join(data.get("task_ids", []))}'
            )
            self._write("  " + "-" * 56)
            return

        if event_type == EventType.PHASE_COMPLETED:
            counts = data.get("counts", {})
            self._write(
                f'  [Phase {data.get("phase")}/{data.get("total_phases")}] '
                f'Completed | Success: {counts.get("success", 0)} | '
                f'Failed: {counts.get("failed", 0)} | Skipped: {counts.get("skipped", 0)}'
            )
            return

        if event_type == EventType.TASK_STARTED:
            self._write(
                f'    [{data.get("task_id")}] Starting: {data.get("title")} '
                f'(agent: {data.get("agent")})'
            )
            return

        if event_type == EventType.TASK_COMPLETED:
            self._write(
                f'    [{data.get("task_id")}] SUCCESS ({data.get("execution_time", 0.0):.1f}s): '
                f'{data.get("summary", "done")}'
            )
            return

        if event_type == EventType.TASK_FAILED:
            self._write(
                f'    [{data.get("task_id")}] FAILED ({data.get("execution_time", 0.0):.1f}s): '
                f'{data.get("error", "Unknown error")}'
            )
            return

        if event_type == EventType.AGENT_RETRY:
            self._write(
                f'    [{data.get("task_id")}] Trying fallback agent: '
                f'{data.get("fallback_agent")}'
            )
            return

        if event_type == EventType.PROJECT_BUILT:
            self._write()
            self._write(f"  📦 PROJECT BUILT: {data.get('project_path', 'project')}/")
            self._write(
                f"  Files: {data.get('file_count', 0)} | "
                f"Entrypoint: {data.get('entrypoint', 'N/A')} | "
                f"Requirements: {data.get('requirements', 'N/A')}"
            )
            return

        if event_type == EventType.RUN_COMPLETED:
            status = data.get("status", "unknown")
            summary = data.get("summary", {})
            counts = summary.get("counts", {})
            self._write()
            self._write("=" * 60)
            self._write("  RESULTS")
            self._write("=" * 60)

            if not self.summary_only:
                for task in data.get("tasks", []):
                    self._write(
                        f'    [{task["status_icon"]}] {task["task_id"]}: '
                        f'{task["title"]} ({task["execution_time"]:.1f}s)'
                    )
                    for block in task.get("code_blocks", []):
                        self._write(
                            f'           {block["language"]}: {block["lines"]} lines'
                        )

            self._write(
                f'\n  Total: {summary.get("total", 0)} tasks | '
                f'Success: {counts.get("success", 0)} | '
                f'Failed: {counts.get("failed", 0)} | '
                f'Skipped: {counts.get("skipped", 0)}'
            )

            total_blocks = data.get("total_blocks", 0)
            total_lines = data.get("total_lines", 0)
            if total_blocks:
                self._write(f"  Code: {total_blocks} blocks, {total_lines} lines")

            self._write("=" * 60)

            error = data.get("error")
            if status == "failed" and error:
                self._write(f"  Error: {error}")

            build_result = data.get("build_result", {})
            files_created = build_result.get("files_created", [])
            if files_created:
                self._write()
                self._write(f"  Project built: {len(files_created)} files created")
                self._write(f'  Location: {data.get("project_dir")}/')
                if build_result.get("entrypoint"):
                    self._write(f'  Entrypoint: {build_result["entrypoint"]}')
                if build_result.get("requirements"):
                    self._write(f'  Requirements: {build_result["requirements"]}')
                if not self.summary_only:
                    self._write()
                    self._write("  Project structure:")
                    for dir_name, dir_path in build_result.get("structure", {}).items():
                        self._write(f"    {dir_name}/")
                        dir_files = [
                            path for path in files_created
                            if path.startswith(dir_path)
                        ]
                        for path in dir_files:
                            self._write(f"      - {path.rsplit('/', 1)[-1]}")

            if data.get("results_file"):
                self._write()
                self._write(f'  Results saved to: {data["results_file"]}')
            return
