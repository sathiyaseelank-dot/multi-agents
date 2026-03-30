"""Unit tests for backend generated.py module."""
import pytest
from backend.generated import process, validate


class TestProcess:
    """Test cases for the process function."""

    def test_process_with_valid_data(self):
        """Test process function with valid input data."""
        input_data = {"key": "value", "number": 42}
        result = process(input_data)
        
        assert result["status"] == "ok"
        assert result["data"] == input_data

    def test_process_with_empty_dict(self):
        """Test process function with empty dictionary."""
        input_data = {}
        result = process(input_data)
        
        assert result["status"] == "ok"
        assert result["data"] == {}

    def test_process_with_nested_data(self):
        """Test process function with nested dictionary."""
        input_data = {
            "user": {"name": "John", "age": 30},
            "items": [1, 2, 3]
        }
        result = process(input_data)
        
        assert result["status"] == "ok"
        assert result["data"] == input_data

    def test_process_preserves_input(self):
        """Test that process function doesn't modify input data."""
        input_data = {"key": "value"}
        original = input_data.copy()
        process(input_data)
        
        assert input_data == original


class TestValidate:
    """Test cases for the validate function."""

    def test_validate_with_non_empty_dict(self):
        """Test validate function with non-empty dictionary."""
        assert validate({"key": "value"}) is True

    def test_validate_with_empty_dict(self):
        """Test validate function with empty dictionary."""
        assert validate({}) is False

    def test_validate_with_nested_dict(self):
        """Test validate function with nested dictionary."""
        assert validate({"nested": {"key": "value"}}) is True

    def test_validate_with_various_values(self):
        """Test validate function with various dictionary values."""
        assert validate({"list": [1, 2, 3]}) is True
        assert validate({"number": 0}) is True
        assert validate({"boolean": False}) is True
        assert validate({"none": None}) is True


class TestIntegration:
    """Integration tests for backend functions."""

    def test_validate_then_process(self):
        """Test workflow: validate data before processing."""
        data = {"user": "test", "action": "create"}
        
        if validate(data):
            result = process(data)
            assert result["status"] == "ok"
        else:
            pytest.fail("Valid data was rejected")

    def test_process_invalid_data(self):
        """Test processing data that should be validated first."""
        empty_data = {}
        
        # Empty data should fail validation
        assert validate(empty_data) is False
        
        # But process will still handle it
        result = process(empty_data)
        assert result["status"] == "ok"
        assert result["data"] == {}

    def test_full_workflow(self):
        """Test complete workflow with multiple data types."""
        test_cases = [
            {"input": {"name": "test"}, "should_validate": True},
            {"input": {}, "should_validate": False},
            {"input": {"nested": {"deep": "value"}}, "should_validate": True},
        ]
        
        for case in test_cases:
            data = case["input"]
            expected_validate = case["should_validate"]
            
            assert validate(data) == expected_validate
            
            if expected_validate:
                result = process(data)
                assert result["status"] == "ok"
                assert result["data"] == data
