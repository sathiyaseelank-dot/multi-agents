"""
End-to-end tests for the calculator interface.
Tests valid calculations, validation feedback, and correct display of results.
"""

import pytest
from calculator import add, subtract, multiply, divide


class TestValidCalculationsE2E:
    """End-to-end tests confirming valid calculations produce correct results."""

    def test_full_addition_workflow(self):
        """E2E: user inputs two numbers, adds them, receives correct result."""
        a, b = 15, 25
        result = add(a, b)
        assert result == 40

    def test_full_subtraction_workflow(self):
        """E2E: user inputs two numbers, subtracts, receives correct result."""
        a, b = 100, 37
        result = subtract(a, b)
        assert result == 63

    def test_full_multiplication_workflow(self):
        """E2E: user inputs two numbers, multiplies, receives correct result."""
        a, b = 12, 8
        result = multiply(a, b)
        assert result == 96

    def test_full_division_workflow(self):
        """E2E: user inputs two numbers, divides, receives correct result."""
        a, b = 81, 9
        result = divide(a, b)
        assert result == 9.0

    def test_chained_operations(self):
        """E2E: sequential operations on accumulated results."""
        step1 = add(10, 5)
        assert step1 == 15
        step2 = subtract(step1, 3)
        assert step2 == 12
        step3 = multiply(step2, 2)
        assert step3 == 24
        step4 = divide(step3, 4)
        assert step4 == 6.0

    def test_all_operations_with_decimals(self):
        """E2E: all operations handle decimal inputs correctly."""
        assert add(1.1, 2.2) == pytest.approx(3.3)
        assert subtract(5.5, 2.2) == pytest.approx(3.3)
        assert multiply(2.5, 4.0) == 10.0
        assert divide(7.5, 2.5) == 3.0

    def test_all_operations_with_negative_numbers(self):
        """E2E: all operations handle negative inputs correctly."""
        assert add(-10, -5) == -15
        assert subtract(-10, -5) == -5
        assert multiply(-4, -3) == 12
        assert divide(-20, -4) == 5.0

    def test_operations_with_zero(self):
        """E2E: operations involving zero produce correct results."""
        assert add(0, 42) == 42
        assert add(42, 0) == 42
        assert subtract(0, 42) == -42
        assert subtract(42, 0) == 42
        assert multiply(0, 999) == 0
        assert multiply(999, 0) == 0
        assert divide(0, 5) == 0.0

    def test_large_number_calculations(self):
        """E2E: operations with large numbers produce correct results."""
        assert add(1e10, 1e10) == 2e10
        assert multiply(1e5, 1e5) == 1e10
        assert divide(1e10, 1e5) == 1e5

    def test_small_number_calculations(self):
        """E2E: operations with very small numbers produce correct results."""
        assert add(1e-10, 1e-10) == pytest.approx(2e-10)
        assert divide(1e-10, 2) == pytest.approx(5e-11)


class TestValidationFeedbackE2E:
    """End-to-end tests confirming validation feedback for invalid inputs."""

    def test_division_by_zero_provides_error(self):
        """E2E: dividing by zero raises ValueError with descriptive message."""
        with pytest.raises(ValueError) as exc_info:
            divide(10, 0)
        assert "Cannot divide by zero" in str(exc_info.value)

    def test_division_by_zero_with_negative_dividend(self):
        """E2E: dividing negative number by zero raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            divide(-42, 0)
        assert "Cannot divide by zero" in str(exc_info.value)

    def test_division_by_zero_with_decimal_dividend(self):
        """E2E: dividing decimal by zero raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            divide(3.14, 0)
        assert "Cannot divide by zero" in str(exc_info.value)

    def test_division_by_zero_error_is_valueerror(self):
        """E2E: division by zero specifically raises ValueError type."""
        with pytest.raises(ValueError):
            divide(1, 0)

    def test_division_by_zero_preserves_other_operations(self):
        """E2E: after division by zero error, other operations still work."""
        with pytest.raises(ValueError):
            divide(10, 0)
        assert add(5, 3) == 8
        assert subtract(10, 4) == 6
        assert multiply(3, 7) == 21

    def test_multiple_division_by_zero_attempts(self):
        """E2E: repeated division by zero consistently raises errors."""
        for _ in range(5):
            with pytest.raises(ValueError, match="Cannot divide by zero"):
                divide(100, 0)


class TestResultDisplayE2E:
    """End-to-end tests confirming correct result values and types."""

    def test_addition_returns_correct_type(self):
        """E2E: addition returns numeric result."""
        result = add(5, 3)
        assert isinstance(result, (int, float))
        assert result == 8

    def test_subtraction_returns_correct_type(self):
        """E2E: subtraction returns numeric result."""
        result = subtract(10, 4)
        assert isinstance(result, (int, float))
        assert result == 6

    def test_multiplication_returns_correct_type(self):
        """E2E: multiplication returns numeric result."""
        result = multiply(6, 7)
        assert isinstance(result, (int, float))
        assert result == 42

    def test_division_returns_float(self):
        """E2E: division always returns float type."""
        result = divide(10, 2)
        assert isinstance(result, float)
        assert result == 5.0

    def test_division_decimal_result_precision(self):
        """E2E: division produces correct decimal precision."""
        result = divide(1, 3)
        assert isinstance(result, float)
        assert result == pytest.approx(0.3333333333333333)

    def test_integer_addition_result(self):
        """E2E: adding two integers produces correct integer result."""
        result = add(3, 4)
        assert result == 7
        assert isinstance(result, int)

    def test_float_addition_result(self):
        """E2E: adding two floats produces correct float result."""
        result = add(1.5, 2.5)
        assert result == 4.0
        assert isinstance(result, float)

    def test_mixed_type_operations(self):
        """E2E: mixing int and float inputs produces correct results."""
        assert add(5, 2.5) == 7.5
        assert subtract(10, 3.5) == 6.5
        assert multiply(4, 2.5) == 10.0
        assert divide(9, 2.0) == 4.5

    def test_commutative_operations(self):
        """E2E: addition and multiplication produce same result regardless of order."""
        assert add(3, 7) == add(7, 3)
        assert multiply(4, 5) == multiply(5, 4)

    def test_non_commutative_operations(self):
        """E2E: subtraction and division respect operand order."""
        assert subtract(10, 3) != subtract(3, 10)
        assert subtract(10, 3) == 7
        assert subtract(3, 10) == -7
        assert divide(10, 2) != divide(2, 10)
        assert divide(10, 2) == 5.0
        assert divide(2, 10) == 0.2

    def test_identity_operations(self):
        """E2E: operations with identity values produce expected results."""
        assert add(42, 0) == 42
        assert subtract(42, 0) == 42
        assert multiply(42, 1) == 42
        assert divide(42, 1) == 42.0

    def test_inverse_operations(self):
        """E2E: inverse operations cancel each other out."""
        value = 7.5
        assert subtract(add(value, 3), 3) == value
        assert divide(multiply(value, 4), 4) == pytest.approx(value)


class TestBoundaryConditionsE2E:
    """End-to-end tests for boundary and edge cases."""

    def test_zero_divided_by_zero_is_invalid(self):
        """E2E: 0/0 raises division by zero error."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(0, 0)

    def test_negative_division(self):
        """E2E: division with one negative operand produces negative result."""
        assert divide(-10, 2) == -5.0
        assert divide(10, -2) == -5.0

    def test_subtraction_to_zero(self):
        """E2E: subtracting a number from itself yields zero."""
        assert subtract(42, 42) == 0
        assert subtract(3.14, 3.14) == pytest.approx(0)

    def test_addition_of_opposites(self):
        """E2E: adding a number and its negative yields zero."""
        assert add(42, -42) == 0
        assert add(-3.14, 3.14) == pytest.approx(0)

    def test_multiply_by_one(self):
        """E2E: multiplying by 1 preserves the value."""
        assert multiply(99, 1) == 99
        assert multiply(-99, 1) == -99
        assert multiply(0, 1) == 0

    def test_multiply_by_negative_one(self):
        """E2E: multiplying by -1 negates the value."""
        assert multiply(99, -1) == -99
        assert multiply(-99, -1) == 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
