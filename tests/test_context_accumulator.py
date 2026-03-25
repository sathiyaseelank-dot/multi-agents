"""Unit tests for the orchestrator context_accumulator module."""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.context_accumulator import ContextAccumulator


class TestContextAccumulator:
    """Tests for ContextAccumulator class."""

    def test_init_default(self):
        """Test default initialization."""
        acc = ContextAccumulator()
        assert acc.epic == ""
        assert acc.get_all_results() == {}

    def test_init_with_epic(self):
        """Test initialization with epic."""
        acc = ContextAccumulator(epic="Build a login system")
        assert acc.epic == "Build a login system"

    def test_add_result_basic(self):
        """Test adding a basic result."""
        acc = ContextAccumulator()
        result = {"summary": "Completed successfully", "code_blocks": []}
        acc.add_result("task-001", "Set up database", result)
        
        results = acc.get_all_results()
        assert "task-001" in results
        assert results["task-001"]["title"] == "Set up database"
        assert results["task-001"]["summary"] == "Completed successfully"

    def test_add_result_with_code_blocks(self):
        """Test adding result with code blocks."""
        acc = ContextAccumulator()
        result = {
            "summary": "Generated API endpoints",
            "code_blocks": [
                {"language": "python", "code": "def api(): pass"},
                {"language": "sql", "code": "SELECT * FROM users"}
            ],
            "files_created": ["api.py", "schema.sql"]
        }
        acc.add_result("task-002", "Create API", result)
        
        results = acc.get_all_results()
        assert len(results["task-002"]["code_blocks"]) == 2
        assert results["task-002"]["files_created"] == ["api.py", "schema.sql"]

    def test_add_result_empty_result(self):
        """Test adding result with None/empty result."""
        acc = ContextAccumulator()
        acc.add_result("task-001", "Empty task", None)
        
        results = acc.get_all_results()
        assert results["task-001"]["summary"] == ""
        assert results["task-001"]["code_blocks"] == []

    def test_add_result_missing_keys(self):
        """Test adding result with missing optional keys."""
        acc = ContextAccumulator()
        result = {"other_key": "value"}  # Missing summary, code_blocks, files_created
        acc.add_result("task-001", "Partial task", result)
        
        results = acc.get_all_results()
        # Implementation uses "completed" as default when result exists but no summary
        assert results["task-001"]["summary"] == "completed"
        assert results["task-001"]["code_blocks"] == []
        assert results["task-001"]["files_created"] == []

    def test_build_context_no_dependencies(self):
        """Test building context with no dependencies."""
        acc = ContextAccumulator(epic="Test epic")
        acc.add_result("task-001", "Task 1", {"summary": "Done"})
        
        context = acc.build_context([])
        assert context["epic"] == "Test epic"
        assert context["completed_tasks"] == []
        assert context["files_created"] == []
        assert context["changed_files"] == []

    def test_build_context_with_dependencies(self):
        """Test building context with dependencies."""
        acc = ContextAccumulator(epic="Build app")
        acc.add_result("task-001", "Database setup", {
            "summary": "DB ready",
            "code_blocks": [{"language": "sql", "code": "CREATE TABLE"}],
            "files_created": ["schema.sql"]
        })
        acc.add_result("task-002", "API setup", {
            "summary": "API ready",
            "code_blocks": [{"language": "python", "code": "def api(): pass"}],
            "files_created": ["api.py"]
        })
        
        context = acc.build_context(["task-001", "task-002"])
        assert context["epic"] == "Build app"
        assert len(context["completed_tasks"]) == 2
        assert len(context["files_created"]) == 2
        assert "schema.sql" in context["files_created"]
        assert "api.py" in context["files_created"]
        assert len(context["workspace_files"]) == 2

    def test_build_context_nonexistent_dependency(self):
        """Test building context with nonexistent dependency."""
        acc = ContextAccumulator()
        acc.add_result("task-001", "Task 1", {"summary": "Done"})
        
        context = acc.build_context(["task-001", "task-999"])
        # Should only include existing task
        assert len(context["completed_tasks"]) == 1

    def test_build_context_files_deduplicated(self):
        """Test that files_created are deduplicated."""
        acc = ContextAccumulator()
        acc.add_result("task-001", "Task 1", {
            "summary": "Done",
            "files_created": ["common.py", "utils.py"]
        })
        acc.add_result("task-002", "Task 2", {
            "summary": "Done",
            "files_created": ["common.py", "main.py"]  # common.py duplicated
        })
        
        context = acc.build_context(["task-001", "task-002"])
        files = context["files_created"]
        assert len(files) == len(set(files))  # All unique
        assert "common.py" in files
        assert "utils.py" in files
        assert "main.py" in files

    def test_get_all_results_returns_dict(self):
        """Test that get_all_results returns a dict with all results."""
        acc = ContextAccumulator()
        acc.add_result("task-001", "Task 1", {"summary": "Done"})
        acc.add_result("task-002", "Task 2", {"summary": "Also done"})
        
        results = acc.get_all_results()
        assert isinstance(results, dict)
        assert len(results) == 2
        assert "task-001" in results
        assert "task-002" in results

    def test_multiple_add_results(self):
        """Test adding multiple results."""
        acc = ContextAccumulator()
        for i in range(5):
            acc.add_result(f"task-{i:03d}", f"Task {i}", {"summary": f"Done {i}"})
        
        results = acc.get_all_results()
        assert len(results) == 5
        for i in range(5):
            assert f"task-{i:03d}" in results
            assert results[f"task-{i:03d}"]["title"] == f"Task {i}"

    def test_changed_files_include_diff_and_content(self):
        acc = ContextAccumulator()
        acc.add_result("task-001", "Task 1", {
            "summary": "Done",
            "files": [{"path": "backend/app.py", "content": "x = 1\n", "operation": "create"}],
        })
        acc.add_result("task-002", "Task 2", {
            "summary": "Done",
            "files": [{"path": "backend/app.py", "content": "x = 2\n", "operation": "update"}],
        })

        context = acc.build_context(["task-002"])
        assert context["changed_files"][0]["path"] == "backend/app.py"
        assert "x = 1" in context["changed_files"][0]["previous_content"]
        assert "x = 2" in context["changed_files"][0]["content"]
        assert "--- backend/app.py:before" in context["changed_files"][0]["diff"]
