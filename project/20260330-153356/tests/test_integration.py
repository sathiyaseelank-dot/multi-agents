"""Integration tests for the multi-agent orchestrator system."""
import pytest
import json
from pathlib import Path
from backend.generated import process, validate


class TestBackendFrontendIntegration:
    """Integration tests between backend and frontend components."""

    def test_backend_process_frontend_display_workflow(self):
        """Test complete workflow: backend processes data, frontend would display it."""
        # Simulate backend processing
        input_data = {
            "session_id": "20260330-120000",
            "status": "COMPLETED",
            "task_description": "Build a REST API",
            "created_at": "2026-03-30 12:00:00",
            "task_count": 5,
        }

        # Backend validates and processes
        assert validate(input_data) is True
        result = process(input_data)

        # Verify processed data structure matches frontend expectations
        assert result["status"] == "ok"
        assert result["data"]["session_id"] == "20260330-120000"
        assert result["data"]["status"] == "COMPLETED"
        assert "task_description" in result["data"]
        assert "created_at" in result["data"]
        assert "task_count" in result["data"]

    def test_empty_data_workflow(self):
        """Test workflow with empty data (no tasks scenario)."""
        empty_data = {}

        # Empty data fails validation
        assert validate(empty_data) is False

        # But process still returns valid structure
        result = process(empty_data)
        assert result["status"] == "ok"
        assert result["data"] == {}

    def test_multiple_tasks_batch(self):
        """Test processing multiple tasks (batch scenario)."""
        tasks = [
            {"session_id": "task-1", "status": "COMPLETED", "task_count": 3},
            {"session_id": "task-2", "status": "FAILED", "task_count": 2},
            {"session_id": "task-3", "status": "EXECUTING", "task_count": 5},
        ]

        # Validate each task
        for task in tasks:
            assert validate(task) is True

        # Process each task
        processed_tasks = [process(task) for task in tasks]

        # Verify all processed successfully
        assert len(processed_tasks) == 3
        assert all(result["status"] == "ok" for result in processed_tasks)

        # Verify data integrity
        for i, task in enumerate(tasks):
            assert processed_tasks[i]["data"] == task


class TestFileStructureIntegration:
    """Tests to verify file structure and imports work correctly."""

    def test_backend_module_exists(self):
        """Test that backend module exists and is importable."""
        backend_path = Path("backend/generated.py")
        assert backend_path.exists()

    def test_test_file_structure(self):
        """Test that test files follow correct structure."""
        test_path = Path("tests/test_generated.py")
        assert test_path.exists()

        # Read and verify test file has proper structure
        content = test_path.read_text()
        assert "import pytest" in content
        assert "from backend.generated import process, validate" in content
        assert "class Test" in content

    def test_react_component_structure(self):
        """Test that React component file exists."""
        component_path = Path("src/components/TaskDashboard.jsx")
        assert component_path.exists()

        content = component_path.read_text()
        assert "import React" in content
        assert "const TaskDashboard" in content
        assert "export default TaskDashboard" in content


class TestStatusMappingIntegration:
    """Integration tests for status mapping between backend and frontend."""

    def test_all_valid_statuses(self):
        """Test that all valid orchestrator statuses are handled."""
        valid_statuses = [
            "COMPLETED",
            "FAILED",
            "EXECUTING",
            "PLANNING",
            "VALIDATING",
            "RUNNING",
        ]

        for status in valid_statuses:
            task_data = {
                "session_id": f"test-{status}",
                "status": status,
                "task_description": f"Task with {status} status",
                "created_at": "2026-03-30",
                "task_count": 1,
            }

            # Backend validation
            assert validate(task_data) is True

            # Backend processing
            result = process(task_data)
            assert result["data"]["status"] == status

    def test_status_transition_workflow(self):
        """Test status transitions in a workflow."""
        workflow = [
            {"status": "INIT", "expected_valid": True},
            {"status": "PLANNING", "expected_valid": True},
            {"status": "EXECUTING", "expected_valid": True},
            {"status": "VALIDATING", "expected_valid": True},
            {"status": "RUNNING", "expected_valid": True},
            {"status": "COMPLETED", "expected_valid": True},
        ]

        for step in workflow:
            task = {
                "session_id": "workflow-test",
                "status": step["status"],
                "task_description": "Workflow test",
                "created_at": "2026-03-30",
                "task_count": 1,
            }

            assert validate(task) == step["expected_valid"]
            result = process(task)
            assert result["data"]["status"] == step["status"]


class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""

    def test_none_input_handling(self):
        """Test handling of None input."""
        with pytest.raises(TypeError):
            validate(None)

    def test_invalid_type_handling(self):
        """Test handling of non-dict types."""
        with pytest.raises(TypeError):
            validate("not a dict")

        with pytest.raises(TypeError):
            validate(["list"])

        with pytest.raises(TypeError):
            validate(123)

    def test_malformed_task_data(self):
        """Test handling of malformed task data."""
        malformed_tasks = [
            {"session_id": None},  # Missing required fields
            {"status": ""},  # Empty status
            {"session_id": "test", "status": "INVALID_STATUS"},  # Invalid status
        ]

        for task in malformed_tasks:
            # Validation still works (checks if dict is non-empty)
            assert validate(task) is True
            result = process(task)
            assert result["status"] == "ok"


class TestPerformanceIntegration:
    """Performance-related integration tests."""

    def test_process_large_dataset(self):
        """Test processing with large dataset."""
        large_data = {
            "session_id": "large-test",
            "status": "COMPLETED",
            "tasks": [{"id": i, "name": f"task-{i}"} for i in range(1000)],
            "metadata": {"created": "2026-03-30", "size": "large"},
        }

        assert validate(large_data) is True
        result = process(large_data)

        assert result["status"] == "ok"
        assert len(result["data"]["tasks"]) == 1000

    def test_process_many_tasks(self):
        """Test processing many tasks quickly."""
        tasks = [
            {
                "session_id": f"task-{i}",
                "status": "COMPLETED",
                "task_description": f"Description {i}",
                "created_at": "2026-03-30",
                "task_count": i,
            }
            for i in range(100)
        ]

        # Validate all
        for task in tasks:
            assert validate(task) is True

        # Process all
        results = [process(task) for task in tasks]

        assert len(results) == 100
        assert all(r["status"] == "ok" for r in results)
