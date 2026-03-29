"""Tests for calculator UI behavior, including valid calculations,
validation messaging, and result rendering across common user flows.

These tests verify the API endpoints that the calculator frontend calls,
ensuring correct behavior for button presses, error display, and result rendering.
"""

import pytest
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import create_app
from config import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestingConfig)
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def calc(client, operation, num1, num2):
    """Helper to call /api/calculator/calculate endpoint."""
    return client.post(
        "/api/calculator/calculate",
        json={"operation": operation, "num1": num1, "num2": num2},
        content_type="application/json",
    )


def parse(resp):
    """Parse JSON response."""
    return json.loads(resp.data)


# ============================================================
# Test: Valid calculation flows (button sequences)
# ============================================================


class TestValidCalculationFlows:
    """Test common user calculation flows that produce correct results."""

    def test_simple_addition_flow(self, client):
        """User presses 5 + 3 = should yield 8."""
        resp = calc(client, "add", 5, 3)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 8
        assert data["error"] is None

    def test_simple_subtraction_flow(self, client):
        """User presses 10 - 4 = should yield 6."""
        resp = calc(client, "subtract", 10, 4)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 6

    def test_simple_multiplication_flow(self, client):
        """User presses 7 x 6 = should yield 42."""
        resp = calc(client, "multiply", 7, 6)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 42

    def test_simple_division_flow(self, client):
        """User presses 20 / 4 = should yield 5."""
        resp = calc(client, "divide", 20, 4)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 5.0

    def test_decimal_addition_flow(self, client):
        """User presses 2.5 + 4.0 = should yield 6.5."""
        resp = calc(client, "add", 2.5, 4.0)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 6.5

    def test_negative_number_flow(self, client):
        """User presses -5 + -3 = should yield -8."""
        resp = calc(client, "add", -5, -3)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == -8

    def test_zero_operand_flow(self, client):
        """User presses 0 + 0 = should yield 0."""
        resp = calc(client, "add", 0, 0)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 0

    def test_large_number_flow(self, client):
        """User presses 999999 + 1 = should yield 1000000."""
        resp = calc(client, "add", 999999, 1)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 1000000

    def test_float_division_flow(self, client):
        """User presses 7 / 2 = should yield 3.5."""
        resp = calc(client, "divide", 7, 2)
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 3.5

    def test_string_number_inputs(self, client):
        """UI sends string numbers from text input fields."""
        resp = calc(client, "add", "10", "5")
        data = parse(resp)
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["result"] == 15.0

    def test_chained_addition_subtraction(self, client):
        """Simulate chained operation: (5 + 3) - 2 = 6."""
        resp1 = calc(client, "add", 5, 3)
        data1 = parse(resp1)
        assert data1["success"] is True

        resp2 = calc(client, "subtract", data1["result"], 2)
        data2 = parse(resp2)
        assert data2["success"] is True
        assert data2["result"] == 6

    def test_chained_multiply_divide(self, client):
        """Simulate chained operation: (6 x 7) / 3 = 14."""
        resp1 = calc(client, "multiply", 6, 7)
        data1 = parse(resp1)
        assert data1["success"] is True

        resp2 = calc(client, "divide", data1["result"], 3)
        data2 = parse(resp2)
        assert data2["success"] is True
        assert data2["result"] == 14.0

    def test_chained_operations_long_sequence(self, client):
        """Simulate: 10 + 5 = 15, 15 - 3 = 12, 12 * 2 = 24, 24 / 4 = 6."""
        resp = calc(client, "add", 10, 5)
        assert parse(resp)["result"] == 15

        resp = calc(client, "subtract", 15, 3)
        assert parse(resp)["result"] == 12

        resp = calc(client, "multiply", 12, 2)
        assert parse(resp)["result"] == 24

        resp = calc(client, "divide", 24, 4)
        assert parse(resp)["result"] == 6.0

    def test_all_operations_in_sequence(self, client):
        """Test all operations work in a single session."""
        operations = [
            ("add", 10, 5, 15),
            ("subtract", 10, 5, 5),
            ("multiply", 10, 5, 50),
            ("divide", 10, 5, 2.0),
        ]
        for op, n1, n2, expected in operations:
            resp = calc(client, op, n1, n2)
            data = parse(resp)
            assert data["success"] is True, f"Failed for operation: {op}"
            assert data["result"] == expected, f"Wrong result for {op}"


# ============================================================
# Test: Validation messaging (error responses)
# ============================================================


class TestValidationMessaging:
    """Test that appropriate error messages are returned for invalid inputs."""

    def test_division_by_zero_shows_error(self, client):
        """Display should show error message for division by zero."""
        resp = calc(client, "divide", 10, 0)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"] is not None
        assert data["error"]["code"] == "DIVISION_BY_ZERO"
        assert "zero" in data["error"]["message"].lower()
        assert data["result"] is None

    def test_division_by_zero_with_negative(self, client):
        """Dividing negative number by zero should show error."""
        resp = calc(client, "divide", -10, 0)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_division_by_zero_with_decimal(self, client):
        """Dividing decimal by zero should show error."""
        resp = calc(client, "divide", 3.14, 0)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_zero_divided_by_zero(self, client):
        """0 / 0 should return division by zero error."""
        resp = calc(client, "divide", 0, 0)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "DIVISION_BY_ZERO"

    def test_invalid_operation_shows_error(self, client):
        """Display should show error for unsupported operation."""
        resp = calc(client, "invalid_op", 5, 3)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_OPERATION"
        assert "unknown" in data["error"]["message"].lower()

    def test_missing_operation_shows_error(self, client):
        """API should return error when operation field is missing."""
        resp = client.post(
            "/api/calculator/calculate",
            json={"num1": 5, "num2": 3},
            content_type="application/json",
        )
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_OPERATION"

    def test_empty_operation_shows_error(self, client):
        """API should return error when operation is empty string."""
        resp = calc(client, "", 5, 3)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_OPERATION"

    def test_whitespace_operation_shows_error(self, client):
        """API should return error when operation is whitespace only."""
        resp = calc(client, "   ", 5, 3)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_OPERATION"

    def test_missing_num1_shows_error(self, client):
        """API should return error when num1 is missing."""
        resp = client.post(
            "/api/calculator/calculate",
            json={"operation": "add", "num2": 3},
            content_type="application/json",
        )
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_OPERAND"
        assert "num1" in data["error"]["message"]

    def test_missing_num2_shows_error(self, client):
        """API should return error when num2 is missing."""
        resp = client.post(
            "/api/calculator/calculate",
            json={"operation": "add", "num1": 5},
            content_type="application/json",
        )
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_OPERAND"
        assert "num2" in data["error"]["message"]

    def test_invalid_num1_type_shows_error(self, client):
        """API should return error when num1 is not a number."""
        resp = calc(client, "add", "abc", 5)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_OPERAND"
        assert "num1" in data["error"]["message"]

    def test_invalid_num2_type_shows_error(self, client):
        """API should return error when num2 is not a number."""
        resp = calc(client, "add", 5, "xyz")
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_OPERAND"
        assert "num2" in data["error"]["message"]

    def test_nan_operand_shows_error(self, client):
        """API should return error for NaN operand."""
        resp = calc(client, "add", float("nan"), 5)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_OPERAND"
        assert "nan" in data["error"]["message"].lower()

    def test_infinity_operand_shows_error(self, client):
        """API should return error for infinity operand."""
        resp = calc(client, "add", float("inf"), 5)
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_OPERAND"
        assert "infinity" in data["error"]["message"].lower()

    def test_empty_body_shows_error(self, client):
        """API should return error when no JSON body is provided."""
        resp = client.post(
            "/api/calculator/calculate",
            content_type="application/json",
        )
        data = parse(resp)
        assert resp.status_code == 400
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_REQUEST"

    def test_error_response_has_consistent_format(self, client):
        """Error responses should always have success, error, result fields."""
        resp = calc(client, "divide", 10, 0)
        data = parse(resp)
        assert "success" in data
        assert "error" in data
        assert "result" in data
        assert data["success"] is False
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert isinstance(data["error"]["code"], str)
        assert isinstance(data["error"]["message"], str)
        assert len(data["error"]["message"]) > 0

    def test_case_insensitive_operation(self, client):
        """Operations should be case-insensitive."""
        resp = calc(client, "ADD", 5, 3)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 8

        resp = calc(client, "Divide", 10, 2)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 5.0

    def test_whitespace_padded_operation(self, client):
        """Operations with surrounding whitespace should work."""
        resp = calc(client, "  add  ", 5, 3)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 8


# ============================================================
# Test: Result rendering (response format)
# ============================================================


class TestResultRendering:
    """Test that results are rendered in the expected format for UI display."""

    def test_success_response_format(self, client):
        """Successful calculation should return proper response structure."""
        resp = calc(client, "add", 5, 3)
        data = parse(resp)
        assert "success" in data
        assert "result" in data
        assert "error" in data
        assert "operation" in data
        assert "operands" in data
        assert data["success"] is True
        assert isinstance(data["result"], (int, float))

    def test_integer_result_rendering(self, client):
        """Integer results should be returned as numbers."""
        resp = calc(client, "multiply", 5, 3)
        data = parse(resp)
        assert data["result"] == 15
        assert isinstance(data["result"], int)

    def test_float_result_rendering(self, client):
        """Float results should maintain precision."""
        resp = calc(client, "divide", 1, 3)
        data = parse(resp)
        assert data["result"] == pytest.approx(0.3333333333333333)

    def test_zero_result_rendering(self, client):
        """Zero results should be rendered as 0."""
        resp = calc(client, "multiply", 0, 999)
        data = parse(resp)
        assert data["result"] == 0

    def test_negative_result_rendering(self, client):
        """Negative results should include minus sign."""
        resp = calc(client, "subtract", 3, 10)
        data = parse(resp)
        assert data["result"] == -7

    def test_large_result_rendering(self, client):
        """Large results should be returned without overflow."""
        resp = calc(client, "multiply", 100000, 100000)
        data = parse(resp)
        assert data["result"] == 10000000000

    def test_small_decimal_result_rendering(self, client):
        """Very small decimal results should maintain precision."""
        resp = calc(client, "divide", 1, 1000000)
        data = parse(resp)
        assert data["result"] == pytest.approx(0.000001)

    def test_operation_metadata_in_response(self, client):
        """Response should include operation metadata for UI display."""
        resp = calc(client, "add", 5, 3)
        data = parse(resp)
        assert data["operation"] == "add"
        assert data["operands"]["num1"] == 5
        assert data["operands"]["num2"] == 3

    def test_division_returns_float(self, client):
        """Division should always return float type."""
        resp = calc(client, "divide", 10, 2)
        data = parse(resp)
        assert isinstance(data["result"], float)
        assert data["result"] == 5.0

    def test_error_result_is_null(self, client):
        """Error responses should have null result."""
        resp = calc(client, "divide", 10, 0)
        data = parse(resp)
        assert data["result"] is None


# ============================================================
# Test: Health endpoint for UI status indicator
# ============================================================


class TestHealthForUI:
    """Test health endpoint used by UI for connection status."""

    def test_health_returns_ok(self, client):
        """Health endpoint should return ok for UI status indicator."""
        resp = client.get("/api/health")
        data = parse(resp)
        assert resp.status_code == 200
        assert data["status"] == "ok"

    def test_health_response_format(self, client):
        """Health response should have expected format for UI."""
        resp = client.get("/api/health")
        data = parse(resp)
        assert "status" in data


# ============================================================
# Test: Complete user flows (end-to-end simulation)
# ============================================================


class TestCompleteUserFlows:
    """Test complete user interaction flows from start to finish."""

    def test_basic_arithmetic_session(self, client):
        """Simulate a session: 5+3=8, then 8-2=6, then 6*2=12."""
        resp = calc(client, "add", 5, 3)
        assert parse(resp)["result"] == 8

        resp = calc(client, "subtract", 8, 2)
        assert parse(resp)["result"] == 6

        resp = calc(client, "multiply", 6, 2)
        assert parse(resp)["result"] == 12

    def test_error_recovery_flow(self, client):
        """Simulate: 10/0=error, then 10/2=5 (recovery)."""
        resp = calc(client, "divide", 10, 0)
        data = parse(resp)
        assert data["success"] is False

        resp = calc(client, "divide", 10, 2)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 5.0

    def test_decimal_input_flow(self, client):
        """Simulate: user enters 3.14 * 2 = 6.28."""
        resp = calc(client, "multiply", 3.14, 2)
        data = parse(resp)
        assert data["result"] == pytest.approx(6.28)

    def test_negative_number_arithmetic_flow(self, client):
        """Simulate: -5 * -3 = 15, then 15 + (-10) = 5."""
        resp = calc(client, "multiply", -5, -3)
        assert parse(resp)["result"] == 15

        resp = calc(client, "add", 15, -10)
        assert parse(resp)["result"] == 5

    def test_complex_expression_flow(self, client):
        """Simulate: (10 + 5) * 2 - 8 / 4 = 28."""
        resp = calc(client, "add", 10, 5)
        step1 = parse(resp)["result"]
        assert step1 == 15

        resp = calc(client, "multiply", step1, 2)
        step2 = parse(resp)["result"]
        assert step2 == 30

        resp = calc(client, "divide", 8, 4)
        step3 = parse(resp)["result"]
        assert step3 == 2.0

        resp = calc(client, "subtract", step2, step3)
        assert parse(resp)["result"] == 28.0

    def test_repeated_equals_press(self, client):
        """Pressing equals multiple times with same operands should give same result."""
        for _ in range(3):
            resp = calc(client, "add", 5, 3)
            data = parse(resp)
            assert data["result"] == 8

    def test_alternating_operations(self, client):
        """Simulate alternating between different operations."""
        resp = calc(client, "add", 10, 5)
        assert parse(resp)["result"] == 15

        resp = calc(client, "multiply", 3, 4)
        assert parse(resp)["result"] == 12

        resp = calc(client, "subtract", 20, 7)
        assert parse(resp)["result"] == 13

        resp = calc(client, "divide", 100, 4)
        assert parse(resp)["result"] == 25.0


# ============================================================
# Test: Edge cases in UI context
# ============================================================


class TestUIEdgeCases:
    """Test edge cases that may occur during user interaction."""

    def test_subtraction_result_zero(self, client):
        """Subtracting equal numbers should yield zero."""
        resp = calc(client, "subtract", 42, 42)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 0

    def test_division_result_one(self, client):
        """Dividing a number by itself should yield one."""
        resp = calc(client, "divide", 7, 7)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 1.0

    def test_multiply_by_zero(self, client):
        """Multiplying by zero should yield zero."""
        resp = calc(client, "multiply", 999, 0)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 0

    def test_multiply_by_one(self, client):
        """Multiplying by one should preserve value."""
        resp = calc(client, "multiply", 42, 1)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 42

    def test_add_zero(self, client):
        """Adding zero should preserve value."""
        resp = calc(client, "add", 42, 0)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 42

    def test_subtract_zero(self, client):
        """Subtracting zero should preserve value."""
        resp = calc(client, "subtract", 42, 0)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 42

    def test_divide_zero_by_number(self, client):
        """Dividing zero by any number should yield zero."""
        resp = calc(client, "divide", 0, 5)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 0.0

    def test_very_long_decimal(self, client):
        """Results with many decimal places should be handled."""
        resp = calc(client, "divide", 1, 7)
        data = parse(resp)
        assert data["success"] is True
        assert isinstance(data["result"], float)

    def test_scientific_notation_input(self, client):
        """Scientific notation numbers should be accepted."""
        resp = calc(client, "multiply", 1e5, 1e5)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 1e10

    def test_negative_zero(self, client):
        """Negative zero should be treated as zero."""
        resp = calc(client, "add", -0.0, 0.0)
        data = parse(resp)
        assert data["success"] is True
        assert data["result"] == 0

    def test_commutative_addition(self, client):
        """Addition should be commutative: a + b = b + a."""
        resp1 = calc(client, "add", 3, 7)
        resp2 = calc(client, "add", 7, 3)
        assert parse(resp1)["result"] == parse(resp2)["result"]

    def test_commutative_multiplication(self, client):
        """Multiplication should be commutative: a * b = b * a."""
        resp1 = calc(client, "multiply", 4, 5)
        resp2 = calc(client, "multiply", 5, 4)
        assert parse(resp1)["result"] == parse(resp2)["result"]

    def test_non_commutative_subtraction(self, client):
        """Subtraction should not be commutative."""
        resp1 = calc(client, "subtract", 10, 3)
        resp2 = calc(client, "subtract", 3, 10)
        assert parse(resp1)["result"] == 7
        assert parse(resp2)["result"] == -7

    def test_non_commutative_division(self, client):
        """Division should not be commutative."""
        resp1 = calc(client, "divide", 10, 2)
        resp2 = calc(client, "divide", 2, 10)
        assert parse(resp1)["result"] == 5.0
        assert parse(resp2)["result"] == 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
