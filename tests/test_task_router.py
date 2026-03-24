"""Unit tests for the orchestrator task_router module."""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.task_router import (
    compute_phases,
    get_fallback_agent,
    compute_execution_summary,
    FALLBACK_MAP,
    AGENT_CAPABILITIES,
)
from orchestrator.task_manager import Task, TaskStatus


class TestFallbackMap:
    """Tests for FALLBACK_MAP configuration."""

    def test_fallback_map_has_all_agents(self):
        """Test that all agents have fallback entries."""
        assert "opencode" in FALLBACK_MAP
        assert "gemini" in FALLBACK_MAP
        assert "kilo" in FALLBACK_MAP

    def test_fallback_map_has_multiple_fallbacks(self):
        """Test that each agent has multiple fallback options."""
        for agent, fallbacks in FALLBACK_MAP.items():
            assert len(fallbacks) >= 2


class TestAgentCapabilities:
    """Tests for AGENT_CAPABILITIES configuration."""

    def test_all_agents_have_capabilities(self):
        """Test that all agents have capability definitions."""
        assert "opencode" in AGENT_CAPABILITIES
        assert "gemini" in AGENT_CAPABILITIES
        assert "kilo" in AGENT_CAPABILITIES

    def test_capabilities_are_sets(self):
        """Test that capabilities are stored as sets."""
        for agent, caps in AGENT_CAPABILITIES.items():
            assert isinstance(caps, set)

    def test_all_task_types_covered(self):
        """Test that all task types are covered by agents."""
        all_caps = set()
        for caps in AGENT_CAPABILITIES.values():
            all_caps.update(caps)
        assert "backend" in all_caps
        assert "frontend" in all_caps
        assert "testing" in all_caps


class TestComputePhases:
    """Tests for compute_phases function."""

    def create_task(self, task_id: str, agent: str = "opencode",
                    task_type: str = "backend", dependencies: list = None) -> Task:
        """Helper to create test tasks."""
        return Task(
            id=task_id,
            title=f"Task {task_id}",
            description=f"Description for {task_id}",
            agent=agent,
            type=task_type,
            dependencies=dependencies or [],
        )

    def test_single_task_no_dependencies(self):
        """Test single task with no dependencies."""
        tasks = [self.create_task("task-001")]
        phases = compute_phases(tasks)
        
        assert len(phases) == 1
        assert len(phases[0]) == 1
        assert phases[0][0].id == "task-001"

    def test_multiple_tasks_no_dependencies(self):
        """Test multiple tasks with no dependencies - all in one phase."""
        tasks = [
            self.create_task("task-001"),
            self.create_task("task-002"),
            self.create_task("task-003"),
        ]
        phases = compute_phases(tasks)
        
        assert len(phases) == 1
        assert len(phases[0]) == 3  # All can run in parallel

    def test_sequential_dependencies(self):
        """Test tasks with sequential dependencies."""
        tasks = [
            self.create_task("task-001"),
            self.create_task("task-002", dependencies=["task-001"]),
            self.create_task("task-003", dependencies=["task-002"]),
        ]
        phases = compute_phases(tasks)
        
        assert len(phases) == 3
        assert phases[0][0].id == "task-001"
        assert phases[1][0].id == "task-002"
        assert phases[2][0].id == "task-003"

    def test_parallel_then_sequential(self):
        """Test parallel tasks followed by sequential task."""
        tasks = [
            self.create_task("task-001"),
            self.create_task("task-002"),
            self.create_task("task-003", dependencies=["task-001", "task-002"]),
        ]
        phases = compute_phases(tasks)
        
        assert len(phases) == 2
        assert len(phases[0]) == 2  # task-001 and task-002 in parallel
        assert len(phases[1]) == 1  # task-003 after both complete

    def test_diamond_dependency(self):
        """Test diamond-shaped dependency pattern."""
        tasks = [
            self.create_task("task-001"),  # Start
            self.create_task("task-002", dependencies=["task-001"]),  # Branch 1
            self.create_task("task-003", dependencies=["task-001"]),  # Branch 2
            self.create_task("task-004", dependencies=["task-002", "task-003"]),  # Join
        ]
        phases = compute_phases(tasks)
        
        assert len(phases) == 3
        assert phases[0][0].id == "task-001"
        assert len(phases[1]) == 2  # task-002 and task-003 in parallel
        assert phases[2][0].id == "task-004"

    def test_empty_task_list(self):
        """Test empty task list."""
        phases = compute_phases([])
        assert phases == []

    def test_circular_dependency_detected(self):
        """Test that circular dependencies are handled."""
        tasks = [
            self.create_task("task-001", dependencies=["task-002"]),
            self.create_task("task-002", dependencies=["task-001"]),
        ]
        phases = compute_phases(tasks)
        
        # Should still return tasks, but in a final "unresolved" phase
        assert len(phases) >= 1
        # All tasks should be in the result
        all_task_ids = {t.id for phase in phases for t in phase}
        assert "task-001" in all_task_ids
        assert "task-002" in all_task_ids

    def test_mixed_agents_in_phase(self):
        """Test that phases can contain tasks for different agents."""
        tasks = [
            self.create_task("task-001", agent="opencode"),
            self.create_task("task-002", agent="gemini"),
            self.create_task("task-003", agent="kilo"),
        ]
        phases = compute_phases(tasks)
        
        assert len(phases) == 1
        agents_in_phase = {t.agent for t in phases[0]}
        assert agents_in_phase == {"opencode", "gemini", "kilo"}


class TestGetFallbackAgent:
    """Tests for get_fallback_agent function."""

    def test_fallback_from_opencode_backend(self):
        """Test fallback from opencode for backend task."""
        fallback = get_fallback_agent("opencode", "backend")
        # Should find a fallback that can do backend
        assert fallback is not None
        assert fallback in ["kilo", "gemini"]

    def test_fallback_from_opencode_testing(self):
        """Test fallback from opencode for testing task."""
        fallback = get_fallback_agent("opencode", "testing")
        assert fallback is not None

    def test_fallback_from_gemini_frontend(self):
        """Test fallback from gemini for frontend task."""
        fallback = get_fallback_agent("gemini", "frontend")
        assert fallback is not None
        assert fallback in ["opencode", "kilo"]

    def test_fallback_from_kilo_testing(self):
        """Test fallback from kilo for testing task."""
        fallback = get_fallback_agent("kilo", "testing")
        assert fallback is not None

    def test_unknown_agent_returns_none(self):
        """Test that unknown agent returns None."""
        fallback = get_fallback_agent("unknown_agent", "backend")
        assert fallback is None

    def test_fallback_respects_capabilities(self):
        """Test that fallback respects task type capabilities."""
        # All agents can handle all task types per AGENT_CAPABILITIES
        for agent in ["opencode", "gemini", "kilo"]:
            for task_type in ["backend", "frontend", "testing"]:
                fallback = get_fallback_agent(agent, task_type)
                assert fallback is not None


class TestComputeExecutionSummary:
    """Tests for compute_execution_summary function."""

    def create_task(self, task_id: str, agent: str = "opencode") -> Task:
        """Helper to create test tasks."""
        return Task(
            id=task_id,
            title=f"Task {task_id}",
            description=f"Description for {task_id}",
            agent=agent,
            type="backend",
            dependencies=[],
        )

    def test_single_phase_sequential(self):
        """Test summary for single task phase."""
        phases = [[self.create_task("task-001")]]
        summary = compute_execution_summary(phases)
        
        assert "Phase 1" in summary
        assert "sequential" in summary
        assert "task-001" in summary

    def test_single_phase_parallel(self):
        """Test summary for parallel task phase."""
        phases = [[
            self.create_task("task-001"),
            self.create_task("task-002"),
        ]]
        summary = compute_execution_summary(phases)
        
        assert "Phase 1" in summary
        assert "parallel" in summary
        assert "task-001" in summary
        assert "task-002" in summary

    def test_multiple_phases(self):
        """Test summary for multiple phases."""
        phases = [
            [self.create_task("task-001", "opencode")],
            [self.create_task("task-002", "gemini")],
            [self.create_task("task-003", "kilo")],
        ]
        summary = compute_execution_summary(phases)
        
        assert "Phase 1" in summary
        assert "Phase 2" in summary
        assert "Phase 3" in summary
        assert "opencode" in summary
        assert "gemini" in summary
        assert "kilo" in summary

    def test_empty_phases(self):
        """Test summary for empty phases."""
        summary = compute_execution_summary([])
        assert summary == ""

    def test_summary_format(self):
        """Test summary output format."""
        phases = [[
            self.create_task("task-001", "opencode"),
            self.create_task("task-002", "gemini"),
        ]]
        summary = compute_execution_summary(phases)
        
        # Format: "  Phase N (mode): [task_ids] via agents"
        lines = summary.split('\n')
        assert len(lines) == 1
        assert "(parallel)" in lines[0]
        assert "via" in lines[0]
