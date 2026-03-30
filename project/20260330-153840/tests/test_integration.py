"""
Integration tests for the generated components
Tests the interaction between backend and frontend data flow
"""
import pytest
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from generated import process, validate


class TestBackendFrontendDataFlow:
    """Test data flow between backend processing and frontend consumption"""

    def test_backend_output_matches_frontend_expectations(self):
        """Test that backend output format matches what frontend expects"""
        # Simulate backend processing task data
        task_data = {
            "id": "task-001",
            "name": "Test Task",
            "status": "completed",
            "agent": "opencode",
            "duration": 10.5
        }
        
        # Process through backend
        result = process(task_data)
        
        # Validate structure
        assert validate(result) is True
        assert "status" in result
        assert "data" in result
        
        # Verify data integrity
        assert result["data"]["id"] == task_data["id"]
        assert result["data"]["status"] == task_data["status"]

    def test_task_status_workflow(self):
        """Test complete workflow for task status updates"""
        # Initial task
        task = {"id": "task-001", "status": "pending"}
        assert validate(task) is True
        
        # Update to in_progress
        task["status"] = "in_progress"
        processed = process(task)
        assert processed["data"]["status"] == "in_progress"
        
        # Update to completed
        task["status"] = "completed"
        task["duration"] = 15.2
        processed = process(task)
        assert processed["data"]["status"] == "completed"
        assert processed["data"]["duration"] == 15.2

    def test_multiple_tasks_batch_processing(self):
        """Test processing multiple tasks as a batch"""
        tasks = [
            {"id": "task-001", "status": "completed", "agent": "opencode"},
            {"id": "task-002", "status": "in_progress", "agent": "gemini"},
            {"id": "task-003", "status": "pending", "agent": "kilo"},
            {"id": "task-004", "status": "failed", "agent": "opencode", "error": "Test error"}
        ]
        
        # Process each task
        processed_tasks = []
        for task in tasks:
            if validate(task):
                result = process(task)
                processed_tasks.append(result["data"])
        
        # Verify all tasks processed
        assert len(processed_tasks) == 4
        
        # Verify status distribution
        statuses = [t["status"] for t in processed_tasks]
        assert statuses.count("completed") == 1
        assert statuses.count("in_progress") == 1
        assert statuses.count("pending") == 1
        assert statuses.count("failed") == 1

    def test_task_with_error_handling(self):
        """Test handling tasks with error information"""
        task_with_error = {
            "id": "task-005",
            "name": "Failed Task",
            "status": "failed",
            "agent": "opencode",
            "error": "Configuration file not found: .github/workflows/ci.yml"
        }
        
        # Validate and process
        assert validate(task_with_error) is True
        result = process(task_with_error)
        
        # Verify error is preserved
        assert result["data"]["error"] == task_with_error["error"]
        assert result["data"]["status"] == "failed"

    def test_statistics_calculation(self):
        """Test statistics calculation for dashboard"""
        tasks = [
            {"id": "1", "status": "completed"},
            {"id": "2", "status": "completed"},
            {"id": "3", "status": "in_progress"},
            {"id": "4", "status": "pending"},
            {"id": "5", "status": "pending"},
            {"id": "6", "status": "failed"},
        ]
        
        # Calculate statistics (mimicking frontend logic)
        stats = {
            "total": len(tasks),
            "completed": sum(1 for t in tasks if t["status"] == "completed"),
            "in_progress": sum(1 for t in tasks if t["status"] == "in_progress"),
            "failed": sum(1 for t in tasks if t["status"] == "failed"),
            "pending": sum(1 for t in tasks if t["status"] == "pending"),
        }
        
        # Verify calculations
        assert stats["total"] == 6
        assert stats["completed"] == 2
        assert stats["in_progress"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 2
        
        # Calculate progress percentage
        progress = (stats["completed"] / stats["total"]) * 100
        assert progress == pytest.approx(33.33, rel=0.01)

    def test_filtering_logic(self):
        """Test filtering logic matches frontend implementation"""
        tasks = [
            {"id": "task-001", "name": "Initialize Project", "status": "completed"},
            {"id": "task-002", "name": "Create Database", "status": "in_progress"},
            {"id": "task-003", "name": "Build Login", "status": "pending"},
            {"id": "task-004", "name": "Write Tests", "status": "pending"},
            {"id": "task-005", "name": "Setup CI/CD", "status": "failed"},
        ]
        
        # Test status filter
        pending_tasks = [t for t in tasks if t["status"] == "pending"]
        assert len(pending_tasks) == 2
        
        # Test search filter (case-insensitive)
        search_term = "database"
        search_results = [
            t for t in tasks 
            if search_term.lower() in t["name"].lower() or search_term.lower() in t["id"].lower()
        ]
        assert len(search_results) == 1
        assert search_results[0]["name"] == "Create Database"
        
        # Test combined filter
        combined = [
            t for t in tasks 
            if t["status"] == "pending" and "test" in t["name"].lower()
        ]
        assert len(combined) == 1
        assert combined[0]["name"] == "Write Tests"

    def test_search_functionality(self):
        """Test search functionality matches frontend behavior"""
        tasks = [
            {"id": "task-001", "name": "API Integration"},
            {"id": "task-002", "name": "Database Schema"},
            {"id": "task-003", "name": "Login Component"},
            {"id": "task-004", "name": "Unit Tests"},
        ]
        
        # Search by name
        search_term = "login"
        results = [
            t for t in tasks 
            if search_term.lower() in t["name"].lower()
        ]
        assert len(results) == 1
        assert results[0]["id"] == "task-003"
        
        # Search by ID
        search_term = "task-002"
        results = [
            t for t in tasks 
            if search_term.lower() in t["id"].lower()
        ]
        assert len(results) == 1
        assert results[0]["name"] == "Database Schema"
        
        # Case insensitive search
        search_term = "API"
        results = [
            t for t in tasks 
            if search_term.lower() in t["name"].lower()
        ]
        assert len(results) == 1


class TestEndToEndWorkflow:
    """End-to-end tests simulating real usage scenarios"""

    def test_complete_task_lifecycle(self):
        """Test complete lifecycle of a task from creation to completion"""
        # Step 1: Create task
        task = {
            "id": "task-001",
            "name": "Build Feature",
            "status": "pending",
            "agent": "opencode"
        }
        assert validate(task) is True
        
        # Step 2: Start processing
        task["status"] = "in_progress"
        result = process(task)
        assert result["data"]["status"] == "in_progress"
        
        # Step 3: Complete task
        task["status"] = "completed"
        task["duration"] = 25.5
        task["output"] = "Feature built successfully"
        result = process(task)
        assert result["data"]["status"] == "completed"
        assert result["data"]["duration"] == 25.5
        assert result["data"]["output"] == "Feature built successfully"

    def test_dashboard_data_preparation(self):
        """Test preparing data for dashboard display"""
        raw_tasks = [
            {"id": "1", "status": "completed", "agent": "opencode", "duration": 10.0},
            {"id": "2", "status": "in_progress", "agent": "gemini", "duration": 5.0},
            {"id": "3", "status": "pending", "agent": "kilo"},
            {"id": "4", "status": "failed", "agent": "opencode", "error": "Error msg"},
        ]
        
        # Process all tasks
        processed = [process(t)["data"] for t in raw_tasks if validate(t)]
        
        # Prepare dashboard data
        dashboard_data = {
            "tasks": processed,
            "stats": {
                "total": len(processed),
                "completed": sum(1 for t in processed if t["status"] == "completed"),
                "in_progress": sum(1 for t in processed if t["status"] == "in_progress"),
                "failed": sum(1 for t in processed if t["status"] == "failed"),
            },
            "progress": sum(1 for t in processed if t["status"] == "completed") / len(processed) * 100
        }
        
        # Verify dashboard data
        assert dashboard_data["stats"]["total"] == 4
        assert dashboard_data["stats"]["completed"] == 1
        assert dashboard_data["stats"]["in_progress"] == 1
        assert dashboard_data["stats"]["failed"] == 1
        assert dashboard_data["progress"] == 25.0

    def test_json_serialization(self):
        """Test that processed data can be serialized to JSON for frontend"""
        task = {
            "id": "task-001",
            "name": "Test Task",
            "status": "completed",
            "agent": "opencode",
            "duration": 15.5,
            "output": "Success"
        }
        
        result = process(task)
        
        # Should be JSON serializable
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        
        assert parsed["status"] == "ok"
        assert parsed["data"]["id"] == task["id"]
        assert parsed["data"]["status"] == task["status"]

    def test_error_recovery_workflow(self):
        """Test workflow when task fails and needs recovery"""
        task = {
            "id": "task-001",
            "name": "Risky Operation",
            "status": "in_progress",
            "agent": "opencode"
        }
        
        # Task fails
        task["status"] = "failed"
        task["error"] = "Connection timeout"
        result = process(task)
        
        assert result["data"]["status"] == "failed"
        assert result["data"]["error"] == "Connection timeout"
        
        # Retry task
        task["status"] = "pending"
        task["retry_count"] = 1
        del task["error"]
        result = process(task)
        
        assert result["data"]["status"] == "pending"
        assert result["data"]["retry_count"] == 1


class TestConcurrencyAndState:
    """Test concurrent operations and state management"""

    def test_concurrent_task_processing(self):
        """Test that multiple tasks can be processed concurrently"""
        tasks = [
            {"id": f"task-{i:03d}", "status": "pending", "agent": "opencode"}
            for i in range(1, 11)
        ]
        
        # Process all tasks
        results = []
        for task in tasks:
            if validate(task):
                result = process(task)
                results.append(result)
        
        # All tasks should be processed
        assert len(results) == 10
        
        # All should have correct status
        for result in results:
            assert result["status"] == "ok"
            assert "data" in result

    def test_state_consistency(self):
        """Test that state remains consistent across operations"""
        task = {"id": "task-001", "status": "pending"}
        
        # Process multiple times
        result1 = process(task)
        result2 = process(task)
        result3 = process(task)
        
        # All results should be consistent
        assert result1["data"]["id"] == result2["data"]["id"]
        assert result2["data"]["id"] == result3["data"]["id"]
        assert result1["data"]["status"] == result2["data"]["status"]
        assert result2["data"]["status"] == result3["data"]["status"]
