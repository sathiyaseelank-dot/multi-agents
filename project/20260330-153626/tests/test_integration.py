"""Integration tests for the multi-agent orchestrator system."""
import pytest
import json
from pathlib import Path
from backend.generated import process, validate


class TestBackendIntegration:
    """Integration tests for backend processing workflow."""

    def test_full_data_processing_pipeline(self):
        """Test complete data processing pipeline."""
        # Simulate incoming data from orchestrator
        orchestrator_data = {
            "task_id": "test-001",
            "task_name": "Build API",
            "agent": "opencode",
            "status": "running",
            "progress": 50
        }
        
        # Validate input
        assert validate(orchestrator_data) is True
        
        # Process data
        result = process(orchestrator_data)
        
        # Verify output
        assert result["status"] == "ok"
        assert result["data"]["task_id"] == "test-001"
        assert result["data"]["agent"] == "opencode"

    def test_batch_processing(self):
        """Test processing multiple tasks in batch."""
        tasks = [
            {"id": "1", "name": "Task 1", "status": "pending"},
            {"id": "2", "name": "Task 2", "status": "running"},
            {"id": "3", "name": "Task 3", "status": "completed"},
        ]
        
        results = []
        for task in tasks:
            if validate(task):
                results.append(process(task))
        
        assert len(results) == 3
        assert all(r["status"] == "ok" for r in results)

    def test_error_handling_workflow(self):
        """Test workflow with error scenarios."""
        # Test with empty data
        empty_data = {}
        assert validate(empty_data) is False
        
        # Test with None-like values
        edge_cases = [
            {"value": None},
            {"empty_string": ""},
            {"zero": 0},
            {"false": False},
        ]
        
        for case in edge_cases:
            # All should validate (non-empty dict)
            assert validate(case) is True
            result = process(case)
            assert result["status"] == "ok"


class TestFileStructure:
    """Integration tests for generated file structure."""

    def test_backend_file_exists(self):
        """Test that backend generated.py file exists."""
        backend_path = Path("backend/generated.py")
        assert backend_path.exists(), "backend/generated.py should exist"

    def test_backend_file_is_valid_python(self):
        """Test that backend file contains valid Python."""
        backend_path = Path("backend/generated.py")
        
        try:
            with open(backend_path, 'r') as f:
                source = f.read()
            compile(source, backend_path, 'exec')
        except SyntaxError as e:
            pytest.fail(f"backend/generated.py has syntax error: {e}")

    def test_backend_functions_callable(self):
        """Test that backend functions are callable."""
        from backend.generated import process, validate
        
        assert callable(process)
        assert callable(validate)

    def test_test_file_exists(self):
        """Test that test file exists."""
        test_path = Path("tests/test_generated.py")
        assert test_path.exists(), "tests/test_generated.py should exist"


class TestReactComponentIntegration:
    """Integration tests for React component structure."""

    def test_component_file_exists(self):
        """Test that TaskStatus component file exists."""
        component_path = Path("src/components/TaskStatus.tsx")
        assert component_path.exists(), "TaskStatus.tsx should exist"

    def test_component_exports_exist(self):
        """Test that component exports are available."""
        index_path = Path("src/components/index.ts")
        assert index_path.exists(), "index.ts should exist"
        
        with open(index_path, 'r') as f:
            content = f.read()
        
        assert 'TaskStatus' in content
        assert 'export' in content

    def test_typescript_syntax_valid(self):
        """Test that TypeScript files have valid syntax."""
        component_path = Path("src/components/TaskStatus.tsx")
        
        with open(component_path, 'r') as f:
            content = f.read()
        
        # Basic syntax checks
        assert 'import React' in content
        assert 'export' in content
        assert 'interface' in content
        assert content.count('{') == content.count('}')


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    def test_complete_orchestration_simulation(self):
        """Simulate complete orchestration workflow."""
        # Step 1: Create task data
        task_data = {
            "session_id": "test-session-001",
            "tasks": [
                {"id": "t1", "name": "Plan", "agent": "codex", "status": "completed"},
                {"id": "t2", "name": "Backend", "agent": "opencode", "status": "running"},
                {"id": "t3", "name": "Frontend", "agent": "gemini", "status": "pending"},
                {"id": "t4", "name": "Test", "agent": "kilo", "status": "pending"},
            ]
        }
        
        # Step 2: Validate task data
        assert validate(task_data) is True
        
        # Step 3: Process task data
        result = process(task_data)
        assert result["status"] == "ok"
        
        # Step 4: Verify all tasks included
        assert len(result["data"]["tasks"]) == 4
        
        # Step 5: Verify task statuses
        statuses = [t["status"] for t in result["data"]["tasks"]]
        assert "completed" in statuses
        assert "running" in statuses
        assert "pending" in statuses

    def test_multi_agent_fallback_simulation(self):
        """Test multi-agent fallback scenario."""
        # Simulate agent availability
        agent_availability = {
            "opencode": True,
            "gemini": False,
            "kilo": True,
            "codex": True,
        }
        
        # Task assigned to unavailable agent
        task = {
            "id": "t1",
            "name": "UI Component",
            "assigned_agent": "gemini",
            "fallback_agents": ["opencode", "kilo"]
        }
        
        # Validate task
        assert validate(task) is True
        
        # Process with fallback logic
        result = process(task)
        assert result["status"] == "ok"
        
        # Verify fallback would work
        primary = task["assigned_agent"]
        if not agent_availability.get(primary, False):
            fallbacks = task["fallback_agents"]
            available_fallback = next(
                (a for a in fallbacks if agent_availability.get(a, False)),
                None
            )
            assert available_fallback is not None

    def test_checkpoint_restore_simulation(self):
        """Test checkpoint and restore workflow."""
        # Create checkpoint data
        checkpoint = {
            "session_id": "test-001",
            "timestamp": "2026-03-30T10:00:00Z",
            "completed_tasks": ["t1", "t2"],
            "pending_tasks": ["t3", "t4"],
            "failed_tasks": [],
        }
        
        # Validate checkpoint
        assert validate(checkpoint) is True
        
        # Process checkpoint
        result = process(checkpoint)
        assert result["status"] == "ok"
        
        # Verify checkpoint data preserved
        assert result["data"]["session_id"] == "test-001"
        assert len(result["data"]["completed_tasks"]) == 2


class TestEdgeCases:
    """Edge case integration tests."""

    def test_large_task_batch(self):
        """Test processing large batch of tasks."""
        large_batch = {
            "tasks": [{"id": str(i), "name": f"Task {i}"} for i in range(100)]
        }
        
        assert validate(large_batch) is True
        result = process(large_batch)
        assert result["status"] == "ok"
        assert len(result["data"]["tasks"]) == 100

    def test_special_characters_in_task_names(self):
        """Test tasks with special characters."""
        task = {
            "name": "Build API (v2.0) [Beta] - Test & Deploy",
            "description": "Handle special chars: @#$%^&*()"
        }
        
        assert validate(task) is True
        result = process(task)
        assert result["status"] == "ok"

    def test_unicode_content(self):
        """Test unicode content in task data."""
        task = {
            "name": "Build 日本語アプリ",
            "description": "Émojis: ✅🔄⏳❌⏭️"
        }
        
        assert validate(task) is True
        result = process(task)
        assert result["status"] == "ok"
        assert result["data"] == task
