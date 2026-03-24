"""Tests for the task manager."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from orchestrator.task_manager import TaskManager, TaskStatus


SAMPLE_PLAN = {
    "epic": "Build a login system",
    "tasks": [
        {"id": "task-001", "title": "Backend API", "description": "Create auth API", "agent": "opencode", "type": "backend", "dependencies": []},
        {"id": "task-002", "title": "Login UI", "description": "Create login form", "agent": "gemini", "type": "frontend", "dependencies": []},
        {"id": "task-003", "title": "Tests", "description": "Write tests", "agent": "kilo", "type": "testing", "dependencies": ["task-001", "task-002"]},
    ],
}


class TestTaskManager:
    def test_load_from_plan(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tasks = tm.load_from_plan(SAMPLE_PLAN)
        assert len(tasks) == 3
        assert "task-001" in tm.tasks

    def test_get_ready_tasks_initial(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        ready = tm.get_ready_tasks()
        # task-001 and task-002 have no deps, task-003 depends on both
        ids = {t.id for t in ready}
        assert ids == {"task-001", "task-002"}

    def test_get_ready_after_completion(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        tm.start_task("task-001")
        tm.complete_task("task-001", result={"summary": "done"})
        tm.start_task("task-002")
        tm.complete_task("task-002", result={"summary": "done"})

        ready = tm.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "task-003"

    def test_task_not_ready_if_dep_pending(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        tm.start_task("task-001")
        tm.complete_task("task-001", result={})
        # task-002 still pending → task-003 not ready
        ready = tm.get_ready_tasks()
        ids = {t.id for t in ready}
        assert "task-003" not in ids
        assert "task-002" in ids

    def test_all_done(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        assert not tm.all_done()

        for tid in ["task-001", "task-002", "task-003"]:
            tm.start_task(tid)
            tm.complete_task(tid, result={})
        assert tm.all_done()

    def test_fail_task(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        tm.start_task("task-001")
        tm.fail_task("task-001", "timeout")
        assert tm.tasks["task-001"].status == TaskStatus.FAILED

    def test_skip_task(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        tm.skip_task("task-003", "dep failed")
        assert tm.tasks["task-003"].status == TaskStatus.SKIPPED

    def test_summary(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        tm.start_task("task-001")
        tm.complete_task("task-001", result={})
        tm.start_task("task-002")
        tm.fail_task("task-002", "error")

        s = tm.summary()
        assert s["total"] == 3
        assert s["counts"]["success"] == 1
        assert s["counts"]["failed"] == 1
        assert s["counts"]["pending"] == 1

    def test_checkpoint(self, tmp_path):
        tm = TaskManager(memory_dir=str(tmp_path))
        tm.load_from_plan(SAMPLE_PLAN)
        tm.save_checkpoint("test-session")
        checkpoint_file = tmp_path / "checkpoint-test-session.json"
        assert checkpoint_file.exists()
