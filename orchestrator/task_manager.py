"""Task lifecycle management — create, track, update task status."""

import json
import uuid
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    id: str
    title: str
    description: str
    agent: str
    type: str  # backend, frontend, testing
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[dict] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class TaskManager:
    def __init__(self, memory_dir: str = "memory"):
        self.tasks: dict[str, Task] = {}
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def load_from_plan(self, plan: dict) -> list[Task]:
        """Create Task objects from a planner output."""
        tasks = []
        for task_data in plan.get("tasks", []):
            task = Task(
                id=task_data.get("id", f"task-{uuid.uuid4().hex[:8]}"),
                title=task_data.get("title", "Untitled"),
                description=task_data.get("description", ""),
                agent=task_data.get("agent", "opencode"),
                type=task_data.get("type", "backend"),
                dependencies=task_data.get("dependencies", []),
            )
            self.tasks[task.id] = task
            tasks.append(task)

        logger.info(f"Loaded {len(tasks)} tasks from plan")
        return tasks

    def apply_replan(self, plan: dict) -> list[Task]:
        """Merge a replanned task graph into the existing task set."""
        updated = []
        for task_data in plan.get("tasks", []):
            task_id = task_data.get("id", f"task-{uuid.uuid4().hex[:8]}")
            existing = self.tasks.get(task_id)
            if existing and existing.status == TaskStatus.SUCCESS:
                continue

            task = existing or Task(
                id=task_id,
                title=task_data.get("title", "Untitled"),
                description=task_data.get("description", ""),
                agent=task_data.get("agent", "opencode"),
                type=task_data.get("type", "backend"),
            )
            task.title = task_data.get("title", task.title)
            task.description = task_data.get("description", task.description)
            task.agent = task_data.get("agent", task.agent)
            task.type = task_data.get("type", task.type)
            task.dependencies = task_data.get("dependencies", task.dependencies)
            task.status = TaskStatus.PENDING
            task.error = None
            task.result = None
            task.started_at = None
            task.completed_at = None
            task.execution_time = 0.0
            self.tasks[task_id] = task
            updated.append(task)

        logger.info("Applied replan with %d task updates", len(updated))
        return updated

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def get_ready_tasks(self) -> list[Task]:
        """Return tasks whose dependencies are all satisfied (success or skipped)."""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps_met = all(
                self.tasks.get(dep) and self.tasks[dep].status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED)
                for dep in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return ready

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self.tasks.values() if t.status == status]

    def start_task(self, task_id: str) -> None:
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        logger.info(f"Task {task_id} started: {task.title}")

    def complete_task(self, task_id: str, result: dict, execution_time: float = 0.0) -> None:
        task = self.tasks[task_id]
        task.status = TaskStatus.SUCCESS
        task.result = result
        task.execution_time = execution_time
        task.completed_at = datetime.now().isoformat()
        logger.info(f"Task {task_id} completed in {execution_time:.1f}s: {task.title}")

    def fail_task(self, task_id: str, error: str, execution_time: float = 0.0) -> None:
        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error = error
        task.execution_time = execution_time
        task.completed_at = datetime.now().isoformat()
        logger.warning(f"Task {task_id} failed: {error}")

    def skip_task(self, task_id: str, reason: str = "") -> None:
        task = self.tasks[task_id]
        task.status = TaskStatus.SKIPPED
        task.error = reason or "Skipped due to dependency failure"
        task.completed_at = datetime.now().isoformat()
        logger.info(f"Task {task_id} skipped: {reason}")

    def all_done(self) -> bool:
        """True if no tasks are pending or running."""
        return all(
            t.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED)
            for t in self.tasks.values()
        )

    def summary(self) -> dict:
        """Return a summary of task statuses."""
        counts = {}
        for task in self.tasks.values():
            counts[task.status.value] = counts.get(task.status.value, 0) + 1
        return {
            "total": len(self.tasks),
            "counts": counts,
            "tasks": [t.to_dict() for t in self.tasks.values()],
        }

    def save_checkpoint(self, session_id: str) -> None:
        """Save current task state to disk for crash recovery."""
        checkpoint = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
        }
        path = self.memory_dir / f"checkpoint-{session_id}.json"
        path.write_text(json.dumps(checkpoint, indent=2))
        logger.debug(f"Checkpoint saved: {path}")

    def load_checkpoint(self, session_id: str) -> bool:
        """Restore task states from a saved checkpoint. Returns True on success."""
        path = self.memory_dir / f"checkpoint-{session_id}.json"
        if not path.exists():
            logger.error(f"Checkpoint not found: {path}")
            return False

        data = json.loads(path.read_text())
        for tid, task_dict in data.get("tasks", {}).items():
            task = Task(
                id=task_dict["id"],
                title=task_dict["title"],
                description=task_dict["description"],
                agent=task_dict["agent"],
                type=task_dict["type"],
                dependencies=task_dict.get("dependencies", []),
                status=TaskStatus(task_dict.get("status", "pending")),
                result=task_dict.get("result"),
                error=task_dict.get("error"),
                execution_time=task_dict.get("execution_time", 0.0),
                created_at=task_dict.get("created_at", ""),
                started_at=task_dict.get("started_at"),
                completed_at=task_dict.get("completed_at"),
            )
            # Tasks stuck in RUNNING state at crash time → reset to PENDING
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.PENDING
                task.started_at = None
                logger.info(f"Reset interrupted task {tid} to PENDING")
            self.tasks[tid] = task

        logger.info(
            f"Checkpoint loaded: {len(self.tasks)} tasks from session {session_id}"
        )
        return True
