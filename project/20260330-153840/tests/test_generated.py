"""Unit tests for backend/generated.py"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from generated import process, validate


class TestProcess:
    """Tests for the process() function"""

    def test_process_with_valid_data(self):
        """Test processing valid dictionary data"""
        input_data = {"key": "value", "number": 42}
        result = process(input_data)
        
        assert result["status"] == "ok"
        assert result["data"] == input_data

    def test_process_with_empty_dict(self):
        """Test processing empty dictionary"""
        input_data = {}
        result = process(input_data)
        
        assert result["status"] == "ok"
        assert result["data"] == {}

    def test_process_with_nested_data(self):
        """Test processing nested dictionary"""
        input_data = {
            "user": {"name": "John", "age": 30},
            "items": [1, 2, 3]
        }
        result = process(input_data)
        
        assert result["status"] == "ok"
        assert result["data"] == input_data
        assert result["data"]["user"]["name"] == "John"

    def test_process_returns_new_dict(self):
        """Test that process returns a new dictionary"""
        input_data = {"key": "value"}
        result = process(input_data)
        
        assert result is not input_data
        assert result["data"] is input_data


class TestValidate:
    """Tests for the validate() function"""

    def test_validate_with_non_empty_dict(self):
        """Test validation with non-empty dictionary"""
        input_data = {"key": "value"}
        result = validate(input_data)
        
        assert result is True

    def test_validate_with_empty_dict(self):
        """Test validation with empty dictionary"""
        input_data = {}
        result = validate(input_data)
        
        assert result is False

    def test_validate_with_nested_dict(self):
        """Test validation with nested dictionary"""
        input_data = {"nested": {"key": "value"}}
        result = validate(input_data)
        
        assert result is True

    def test_validate_preserves_truthiness(self):
        """Test that validate uses Python's bool() truthiness"""
        assert validate({"a": 1}) is True
        assert validate({"a": 0}) is True  # Dict with content is truthy
        assert validate({}) is False


class TestIntegration:
    """Integration tests for process and validate together"""

    def test_validate_then_process(self):
        """Test validation before processing"""
        input_data = {"task": "test", "status": "pending"}
        
        if validate(input_data):
            result = process(input_data)
            assert result["status"] == "ok"
            assert result["data"]["task"] == "test"

    def test_process_result_is_valid(self):
        """Test that process output can be validated"""
        input_data = {"key": "value"}
        result = process(input_data)
        
        assert validate(result) is True
        assert validate(result["data"]) is True

    def test_empty_data_workflow(self):
        """Test workflow with empty data"""
        input_data = {}
        
        is_valid = validate(input_data)
        assert is_valid is False
        
        # Process should still work with empty dict
        result = process(input_data)
        assert result["status"] == "ok"
        assert result["data"] == {}
