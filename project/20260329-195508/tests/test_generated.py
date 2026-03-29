"""
Generated test suite for the calculator module.
Provides additional coverage for calculator operations and UI components.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from calculator import (
    CalculatorUI,
    Operation,
    ValidationResult,
    CalculationResult,
    add,
    subtract,
    multiply,
    divide,
)


class TestAddGenerated:
    """Generated tests for addition operation."""

    def test_add_positive(self):
        assert add(2, 3) == 5

    def test_add_negative(self):
        assert add(-2, -3) == -5

    def test_add_mixed(self):
        assert add(-2, 3) == 1

    def test_add_zeros(self):
        assert add(0, 0) == 0

    def test_add_floats(self):
        assert add(1.5, 2.5) == 4.0


class TestSubtractGenerated:
    """Generated tests for subtraction operation."""

    def test_subtract_positive(self):
        assert subtract(10, 4) == 6

    def test_subtract_negative_result(self):
        assert subtract(4, 10) == -6

    def test_subtract_zeros(self):
        assert subtract(0, 0) == 0


class TestMultiplyGenerated:
    """Generated tests for multiplication operation."""

    def test_multiply_positive(self):
        assert multiply(3, 4) == 12

    def test_multiply_by_zero(self):
        assert multiply(5, 0) == 0

    def test_multiply_negative(self):
        assert multiply(-3, -4) == 12

    def test_multiply_mixed_sign(self):
        assert multiply(-3, 4) == -12


class TestDivideGenerated:
    """Generated tests for division operation."""

    def test_divide_positive(self):
        assert divide(10, 2) == 5.0

    def test_divide_float_result(self):
        assert divide(7, 2) == 3.5

    def test_divide_negative(self):
        assert divide(-10, 2) == -5.0

    def test_divide_by_zero_raises(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)


class TestCalculatorUIGenerated:
    """Generated tests for CalculatorUI class."""

    def test_initial_state(self):
        calc = CalculatorUI()
        assert calc.operand_a is None
        assert calc.operand_b is None
        assert calc.operation is None
        assert calc.history == []
        assert calc.validation_messages == []

    def test_set_operand_a_valid(self):
        calc = CalculatorUI()
        result = calc.set_operand_a("42")
        assert result.is_valid is True
        assert calc.operand_a == 42.0

    def test_set_operand_a_invalid(self):
        calc = CalculatorUI()
        result = calc.set_operand_a("not_a_number")
        assert result.is_valid is False
        assert calc.operand_a is None

    def test_set_operand_a_empty(self):
        calc = CalculatorUI()
        result = calc.set_operand_a("")
        assert result.is_valid is False

    def test_set_operand_b_valid(self):
        calc = CalculatorUI()
        result = calc.set_operand_b("3.14")
        assert result.is_valid is True
        assert calc.operand_b == 3.14

    def test_set_operand_b_invalid(self):
        calc = CalculatorUI()
        result = calc.set_operand_b("abc")
        assert result.is_valid is False

    def test_select_operation_valid(self):
        calc = CalculatorUI()
        result = calc.select_operation("add")
        assert result.is_valid is True
        assert calc.operation == Operation.ADD

    def test_select_operation_invalid(self):
        calc = CalculatorUI()
        result = calc.select_operation("invalid_op")
        assert result.is_valid is False

    def test_select_operation_case_insensitive(self):
        calc = CalculatorUI()
        result = calc.select_operation("MULTIPLY")
        assert result.is_valid is True
        assert calc.operation == Operation.MULTIPLY

    def test_calculate_addition(self):
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 15.0

    def test_calculate_subtraction(self):
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("3")
        calc.select_operation("subtract")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 7.0

    def test_calculate_multiplication(self):
        calc = CalculatorUI()
        calc.set_operand_a("4")
        calc.set_operand_b("5")
        calc.select_operation("multiply")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 20.0

    def test_calculate_division(self):
        calc = CalculatorUI()
        calc.set_operand_a("20")
        calc.set_operand_b("4")
        calc.select_operation("divide")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 5.0

    def test_calculate_division_by_zero(self):
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("0")
        calc.select_operation("divide")
        result = calc.calculate()
        assert result.success is False
        assert "Cannot divide by zero" in result.error_message

    def test_calculate_modulo(self):
        calc = CalculatorUI()
        calc.set_operand_a("17")
        calc.set_operand_b("5")
        calc.select_operation("modulo")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 2.0

    def test_calculate_power(self):
        calc = CalculatorUI()
        calc.set_operand_a("2")
        calc.set_operand_b("10")
        calc.select_operation("power")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 1024.0

    def test_calculate_missing_operand_a(self):
        calc = CalculatorUI()
        calc.set_operand_b("5")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is False

    def test_calculate_missing_operand_b(self):
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is False

    def test_calculate_missing_operation(self):
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("3")
        result = calc.calculate()
        assert result.success is False

    def test_reset(self):
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("add")
        calc.reset()
        assert calc.operand_a is None
        assert calc.operand_b is None
        assert calc.operation is None

    def test_history_tracking(self):
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("3")
        calc.select_operation("add")
        calc.calculate()
        assert len(calc.history) == 1
        assert calc.history[0].success is True

    def test_clear_history(self):
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("3")
        calc.select_operation("add")
        calc.calculate()
        calc.clear_history()
        assert len(calc.history) == 0

    def test_get_display_result_empty(self):
        calc = CalculatorUI()
        assert "No calculations yet" in calc.get_display_result()

    def test_get_display_result_success(self):
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("add")
        calc.calculate()
        display = calc.get_display_result()
        assert "Result:" in display

    def test_get_error_messages(self):
        calc = CalculatorUI()
        calc.set_operand_a("invalid")
        errors = calc.get_error_messages()
        assert len(errors) > 0

    def test_clear_validation_messages(self):
        calc = CalculatorUI()
        calc.set_operand_a("invalid")
        calc.clear_validation_messages()
        assert len(calc.validation_messages) == 0


class TestValidationResultGenerated:
    """Generated tests for ValidationResult dataclass."""

    def test_valid_result(self):
        result = ValidationResult(is_valid=True, message="OK")
        assert result.is_valid is True
        assert result.message == "OK"
        assert result.field is None

    def test_invalid_result_with_field(self):
        result = ValidationResult(is_valid=False, message="Error", field="operand_a")
        assert result.is_valid is False
        assert result.field == "operand_a"


class TestCalculationResultGenerated:
    """Generated tests for CalculationResult dataclass."""

    def test_success_result(self):
        result = CalculationResult(
            success=True, result=42.0, expression="40 + 2 = 42.0"
        )
        assert result.success is True
        assert result.result == 42.0
        assert result.error_message is None

    def test_failure_result(self):
        result = CalculationResult(
            success=False, result=None, expression="", error_message="Error"
        )
        assert result.success is False
        assert result.result is None


class TestEdgeCasesGenerated:
    """Generated tests for edge cases."""

    def test_very_large_numbers(self):
        assert add(1e100, 1e100) == 2e100

    def test_very_small_numbers(self):
        result = add(1e-100, 1e-100)
        assert result > 0

    def test_zero_operations(self):
        assert add(0, 5) == 5
        assert subtract(0, 5) == -5
        assert multiply(0, 5) == 0

    def test_negative_exponent(self):
        calc = CalculatorUI()
        calc.set_operand_a("2")
        calc.set_operand_b("-3")
        calc.select_operation("power")
        result = calc.calculate()
        assert result.success is True
        assert abs(result.result - 0.125) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
