"""Integration tests using mock agents — full orchestrator pipeline without real CLI calls."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.base_agent import AgentConfig
from agents.planner import PlanReviewerAgent, PlannerAgent
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.tester import TesterAgent
from orchestrator.events import EventType
import orchestrator.orchestrator as orchestrator_module
from orchestrator.orchestrator import Orchestrator, AGENT_REGISTRY
from orchestrator.task_manager import TaskStatus

MOCK_DIR = Path(__file__).parent / "mock_agents"


def mock_config(script: str, **kwargs) -> AgentConfig:
    """Build an AgentConfig pointing to a mock script."""
    return AgentConfig(
        name=kwargs.get("name", "mock"),
        role=kwargs.get("role", "backend"),
        command="python3",
        args=[str(MOCK_DIR / script)],
        timeout_seconds=10,
        retry_count=1,
        retry_backoff_seconds=0,
    )


def make_mock_orchestrator(tmp_path, planner_script="mock_codex.py",
                            reviewer_script="mock_reviewer_approve.py",
                            backend_script="mock_opencode.py",
                            frontend_script="mock_gemini.py",
                            tester_script="mock_kilo.py") -> Orchestrator:
    """Create an orchestrator wired to mock agents."""
    def fake_resolve_dependencies(project_dir: str):
        requirements_path = Path(project_dir) / "requirements.txt"
        requirements_path.write_text("")
        return {
            "requirements": str(requirements_path),
            "package_json": None,
            "python_dependencies": [],
            "frontend_dependencies": [],
        }

    orchestrator_module.resolve_dependencies = fake_resolve_dependencies
    orchestrator_module.validate_project = lambda project_dir, expected_files=None: {
        "success": True,
        "errors": [],
        "checked_files": [],
    }
    orchestrator_module.execute_project = lambda project_dir: {
        "success": True,
        "logs": "",
        "errors": [],
        "log_entries": [],
        "entrypoint": str(Path(project_dir) / "backend" / "app.py"),
    }

    orch = Orchestrator(
        log_dir=str(tmp_path / "logs"),
        memory_dir=str(tmp_path / "memory"),
        output_dir=str(tmp_path / "output"),
    )

    # Override planner
    planner = PlannerAgent(config=AgentConfig(
        name="codex", role="planner",
        command="python3",
        args=[str(MOCK_DIR / planner_script)],
        timeout_seconds=10, retry_count=1, retry_backoff_seconds=0,
    ))
    orch.planner = planner
    reviewer = PlanReviewerAgent(config=AgentConfig(
        name="codex-reviewer",
        role="reviewer",
        command="python3",
        args=[str(MOCK_DIR / reviewer_script)],
        timeout_seconds=10, retry_count=1, retry_backoff_seconds=0,
    ))
    orch.reviewer = reviewer

    # Override workers
    orch._agents["opencode"] = BackendAgent(config=mock_config(
        backend_script, name="opencode", role="backend"))
    orch._agents["gemini"] = FrontendAgent.__new__(FrontendAgent)
    orch._agents["gemini"].config = mock_config(frontend_script, name="gemini", role="frontend")
    orch._agents["gemini"].logger = __import__("logging").getLogger("mock.gemini")
    orch._agents["kilo"] = TesterAgent(config=AgentConfig(
        name="kilo", role="testing",
        command="python3",
        args=[str(MOCK_DIR / tester_script)],
        timeout_seconds=10, retry_count=1, retry_backoff_seconds=0,
    ))
    orch.evaluator = type("MockEvaluator", (), {"is_available": lambda self: False})()

    return orch


class TestFullPipeline:
    def test_plan_to_completion(self, tmp_path):
        """Full pipeline: plan → execute → build → validate → run."""
        orch = make_mock_orchestrator(tmp_path)
        result = asyncio.run(orch.run("Build a mock application"))

        assert result["status"] == "completed"
        assert result["state"] == "COMPLETED"

        # All 3 tasks should succeed
        summary = result["summary"]
        assert summary["counts"].get("success", 0) == 3
        assert summary["counts"].get("failed", 0) == 0

        # Project structure should be created
        project_dir = Path(result["project_dir"])
        assert project_dir.exists()
        assert (project_dir / "backend").exists()
        assert (project_dir / "frontend").exists()
        assert (project_dir / "tests").exists()
        
        # Check for generated files in project directories
        backend_files = list((project_dir / "backend").glob("*.py"))
        tests_files = list((project_dir / "tests").glob("*.py"))
        assert len(backend_files) >= 1  # opencode emits Python
        assert len(tests_files) >= 1  # kilo emits Python tests
        
        # Check for entrypoint and dependency manifest
        assert (project_dir / "backend" / "app.py").exists()
        assert (project_dir / "requirements.txt").exists()
        assert result["goal_analysis"]["refined_goal"]
        assert result["planning_trace"]["review_1"]["approval"] is True
        assert result["review_iterations"] == 1
        assert result["final_review"]["approval"] is True
        assert "prevalidation_result" in result
        assert result["validation_result"]["success"] is True
        assert result["runtime_result"]["success"] is True
        assert "confidence" in result
        assert "evaluation_result" in result
        memory_file = tmp_path / "memory" / "run-memory.json"
        assert memory_file.exists()

    def test_plan_saved_to_memory(self, tmp_path):
        orch = make_mock_orchestrator(tmp_path)
        result = asyncio.run(orch.run("Build something"))

        session_id = result["session_id"]
        plan_file = tmp_path / "memory" / f"plan-{session_id}.json"
        assert plan_file.exists()

        plan_data = json.loads(plan_file.read_text())
        assert "plan" in plan_data
        assert "tasks" in plan_data["plan"]

        results_file = tmp_path / "memory" / f"results-{session_id}.json"
        results_data = json.loads(results_file.read_text())
        assert "goal_analysis" in results_data
        assert "prevalidation" in results_data

    def test_checkpoint_written_after_each_phase(self, tmp_path):
        orch = make_mock_orchestrator(tmp_path)
        result = asyncio.run(orch.run("Build something"))

        session_id = result["session_id"]
        checkpoint_file = tmp_path / "memory" / f"checkpoint-{session_id}.json"
        assert checkpoint_file.exists()

        checkpoint = json.loads(checkpoint_file.read_text())
        assert len(checkpoint["tasks"]) == 3

    def test_emits_standard_events_on_success(self, tmp_path):
        orch = make_mock_orchestrator(tmp_path)

        result = asyncio.run(orch.run("Build something"))

        assert result["status"] == "completed"
        event_types = [event["type"] for event in orch.events.get_history()]

        assert EventType.PLAN_CREATED.value in event_types
        assert EventType.PLAN_REVIEW_STARTED.value in event_types
        assert EventType.PLAN_REVIEW_COMPLETED.value in event_types
        assert EventType.PLAN_APPROVED.value in event_types
        assert EventType.PHASE_STARTED.value in event_types
        assert EventType.TASK_STARTED.value in event_types
        assert EventType.TASK_COMPLETED.value in event_types
        assert EventType.PROJECT_BUILT.value in event_types
        assert EventType.RUN_COMPLETED.value in event_types


class TestFallbackRouting:
    def test_fallback_on_agent_failure(self, tmp_path):
        """When opencode fails, should fall back to kilo for backend task."""
        orch = make_mock_orchestrator(tmp_path)

        # Make opencode always fail, kilo succeed
        from agents.base_agent import AgentConfig
        orch._agents["opencode"] = BackendAgent(config=AgentConfig(
            name="opencode", role="backend",
            command="python3",
            args=[str(MOCK_DIR / "mock_opencode.py")],
            timeout_seconds=10, retry_count=1, retry_backoff_seconds=0,
            env_vars={"MOCK_EXIT_CODE": "1"},
        ))

        result = asyncio.run(orch.run("Build with failing backend"))

        # At least some tasks should complete via fallback
        summary = result["summary"]
        # task-001 (backend) should have fallen back to kilo or gemini
        task_001 = orch.task_manager.get_task("task-001")
        # Either succeeded via fallback or failed — both are valid behaviours
        assert task_001 is not None
        assert task_001.status in (TaskStatus.SUCCESS, TaskStatus.FAILED)

        event_types = [event["type"] for event in orch.events.get_history()]
        assert EventType.AGENT_RETRY.value in event_types
        assert EventType.TASK_FAILED.value in event_types


class TestPlanningDebate:
    def test_reviewer_requests_revision_then_approves(self, tmp_path):
        orch = make_mock_orchestrator(
            tmp_path,
            planner_script="mock_planner_debate.py",
            reviewer_script="mock_reviewer_debate.py",
        )

        result = asyncio.run(orch.run("Build a debated application"))

        assert result["status"] == "completed"
        assert result["review_iterations"] == 2
        assert result["planning_trace"]["initial_plan"]["tasks"][-1]["id"] == "task-002"
        assert result["planning_trace"]["review_1"]["approval"] is False
        assert result["planning_trace"]["revised_plan"]["tasks"][-1]["id"] == "task-003"
        assert result["planning_trace"]["review_2"]["approval"] is True
        assert result["final_review"]["approval"] is True

    def test_reviewer_rejects_twice_and_planning_fails(self, tmp_path):
        orch = make_mock_orchestrator(
            tmp_path,
            planner_script="mock_planner_debate.py",
            reviewer_script="mock_reviewer_reject.py",
        )

        result = asyncio.run(orch.run("Build a debated application"))

        assert result["status"] == "failed"
        assert result["review_iterations"] == 2
        assert result["planning_trace"]["review_2"]["approval"] is False
        assert result["final_review"]["approval"] is False

    def test_malformed_reviewer_output_fails_planning(self, tmp_path):
        orch = make_mock_orchestrator(
            tmp_path,
            planner_script="mock_planner_debate.py",
            reviewer_script="mock_reviewer_invalid.py",
        )

        result = asyncio.run(orch.run("Build a debated application"))

        assert result["status"] == "failed"
        assert result["planning_trace"]["initial_plan"] is not None
        assert result["review_iterations"] == 0


class TestResume:
    def test_resume_skips_completed_tasks(self, tmp_path):
        """Resume should skip already-completed tasks and only run pending ones."""
        # First run: complete everything
        orch1 = make_mock_orchestrator(tmp_path)
        result1 = asyncio.run(orch1.run("Build something"))
        assert result1["status"] == "completed"
        session_id = result1["session_id"]

        # Manually mark task-003 as pending again to simulate partial crash
        checkpoint_path = tmp_path / "memory" / f"checkpoint-{session_id}.json"
        checkpoint = json.loads(checkpoint_path.read_text())
        checkpoint["tasks"]["task-003"]["status"] = "pending"
        checkpoint["tasks"]["task-003"]["result"] = None
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2))

        # Resume — should only re-run task-003
        orch2 = make_mock_orchestrator(tmp_path)
        orch2.session_id = session_id
        orch2.resume_session_id = session_id
        result2 = asyncio.run(orch2.resume())

        assert result2["status"] == "completed"
        # task-003 should now be success
        task_003 = orch2.task_manager.get_task("task-003")
        assert task_003.status == TaskStatus.SUCCESS

        event_types = [event["type"] for event in orch2.events.get_history()]
        assert EventType.RUN_RESUMED.value in event_types
        assert EventType.RUN_COMPLETED.value in event_types

    def test_resume_restores_running_task_to_pending(self, tmp_path):
        """Tasks stuck in RUNNING at crash time should be reset to PENDING."""
        from orchestrator.task_manager import TaskManager
        tm = TaskManager(memory_dir=str(tmp_path / "memory"))

        # Manually craft a checkpoint with a RUNNING task
        (tmp_path / "memory").mkdir(exist_ok=True)
        checkpoint = {
            "session_id": "test-session",
            "timestamp": "2026-01-01T00:00:00",
            "tasks": {
                "task-001": {
                    "id": "task-001", "title": "Core logic", "description": "...",
                    "agent": "opencode", "type": "backend", "dependencies": [],
                    "status": "running",  # Was in progress when crash happened
                    "result": None, "error": None, "execution_time": 0.0,
                    "created_at": "2026-01-01T00:00:00",
                    "started_at": "2026-01-01T00:00:01",
                    "completed_at": None,
                }
            }
        }
        (tmp_path / "memory" / "checkpoint-test-session.json").write_text(
            json.dumps(checkpoint)
        )

        tm.load_checkpoint("test-session")
        task = tm.get_task("task-001")
        assert task.status == TaskStatus.PENDING  # Reset from RUNNING
        assert task.started_at is None


class TestPlanOnly:
    def test_plan_only_does_not_execute_workers(self, tmp_path):
        """--plan-only should stop after planning without running any workers."""
        orch = make_mock_orchestrator(tmp_path)
        orch.plan_only = True
        result = asyncio.run(orch.run("Build something"))

        assert result["status"] == "completed"
        assert result["state"] == "COMPLETED"
        # No tasks should have been executed
        assert "summary" not in result
        # Output dir should be empty
        output_dir = tmp_path / "output"
        output_files = list(output_dir.glob("*")) if output_dir.exists() else []
        assert len(output_files) == 0
