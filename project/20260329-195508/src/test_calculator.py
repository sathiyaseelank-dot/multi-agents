"""
Comprehensive test suite for the calculator module.
Covers validation, operations, UI components, and edge cases.
"""

import pytest
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


class TestCoreOperations:
    """Test basic arithmetic operations."""

    def test_add_positive_numbers(self):
        """Test addition of positive numbers."""
        assert add(5, 3) == 8
        assert add(10.5, 4.5) == 15.0

    def test_add_negative_numbers(self):
        """Test addition with negative numbers."""
        assert add(-5, -3) == -8
        assert add(-5, 3) == -2

    def test_add_zero(self):
        """Test addition with zero."""
        assert add(0, 5) == 5
        assert add(5, 0) == 5

    def test_subtract_positive_numbers(self):
        """Test subtraction of positive numbers."""
        assert subtract(10, 4) == 6
        assert subtract(5.5, 2.5) == 3.0

    def test_subtract_negative_result(self):
        """Test subtraction resulting in negative."""
        assert subtract(3, 8) == -5

    def test_multiply_positive_numbers(self):
        """Test multiplication of positive numbers."""
        assert multiply(4, 5) == 20
        assert multiply(2.5, 4) == 10.0

    def test_multiply_by_zero(self):
        """Test multiplication by zero."""
        assert multiply(100, 0) == 0
        assert multiply(0, 50) == 0

    def test_multiply_negative_numbers(self):
        """Test multiplication with negative numbers."""
        assert multiply(-5, -3) == 15
        assert multiply(-5, 3) == -15

    def test_divide_positive_numbers(self):
        """Test division of positive numbers."""
        assert divide(10, 2) == 5.0
        assert divide(7.5, 2.5) == 3.0

    def test_divide_by_zero_raises_error(self):
        """Test that division by zero raises ValueError."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)

    def test_divide_result_in_decimal(self):
        """Test division resulting in decimal."""
        assert divide(7, 2) == 3.5


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True, message="Valid")
        assert result.is_valid is True
        assert result.message == "Valid"
        assert result.field is None

    def test_invalid_result_with_field(self):
        """Test creating an invalid result with field."""
        result = ValidationResult(
            is_valid=False,
            message="Invalid input",
            field="operand_a"
        )
        assert result.is_valid is False
        assert result.message == "Invalid input"
        assert result.field == "operand_a"


class TestCalculationResult:
    """Test CalculationResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful calculation result."""
        result = CalculationResult(
            success=True,
            result=10.0,
            expression="5 + 5 = 10.0"
        )
        assert result.success is True
        assert result.result == 10.0
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed calculation result."""
        result = CalculationResult(
            success=False,
            result=None,
            expression="",
            error_message="Division by zero"
        )
        assert result.success is False
        assert result.result is None
        assert result.error_message == "Division by zero"


class TestCalculatorUI:
    """Test CalculatorUI class."""

    def test_initial_state(self):
        """Test calculator initial state."""
        calc = CalculatorUI()
        assert calc.operand_a is None
        assert calc.operand_b is None
        assert calc.operation is None
        assert len(calc.history) == 0
        assert len(calc.validation_messages) == 0

    def test_set_valid_operand_a(self):
        """Test setting valid first operand."""
        calc = CalculatorUI()
        result = calc.set_operand_a("10")
        assert result.is_valid is True
        assert calc.operand_a == 10.0

    def test_set_valid_operand_b(self):
        """Test setting valid second operand."""
        calc = CalculatorUI()
        result = calc.set_operand_b("25.5")
        assert result.is_valid is True
        assert calc.operand_b == 25.5

    def test_set_empty_operand_a(self):
        """Test setting empty first operand."""
        calc = CalculatorUI()
        result = calc.set_operand_a("")
        assert result.is_valid is False
        assert "cannot be empty" in result.message
        assert calc.operand_a is None

    def test_set_empty_operand_b(self):
        """Test setting empty second operand."""
        calc = CalculatorUI()
        result = calc.set_operand_b("")
        assert result.is_valid is False
        assert "cannot be empty" in result.message
        assert calc.operand_b is None

    def test_set_invalid_operand_a(self):
        """Test setting invalid first operand."""
        calc = CalculatorUI()
        result = calc.set_operand_a("abc")
        assert result.is_valid is False
        assert "must be a valid number" in result.message
        assert calc.operand_a is None

    def test_set_invalid_operand_b(self):
        """Test setting invalid second operand."""
        calc = CalculatorUI()
        result = calc.set_operand_b("xyz123")
        assert result.is_valid is False
        assert "must be a valid number" in result.message
        assert calc.operand_b is None

    def test_set_negative_operand(self):
        """Test setting negative operands."""
        calc = CalculatorUI()
        result_a = calc.set_operand_a("-15")
        result_b = calc.set_operand_b("-5")
        assert result_a.is_valid is True
        assert result_b.is_valid is True
        assert calc.operand_a == -15.0
        assert calc.operand_b == -5.0

    def test_set_decimal_operand(self):
        """Test setting decimal operands."""
        calc = CalculatorUI()
        result = calc.set_operand_a("3.14159")
        assert result.is_valid is True
        assert calc.operand_a == 3.14159


class TestCalculatorUIOperations:
    """Test CalculatorUI operation selection."""

    def test_select_valid_operation(self):
        """Test selecting valid operations."""
        calc = CalculatorUI()
        for op in ["add", "subtract", "multiply", "divide", "modulo", "power"]:
            result = calc.select_operation(op)
            assert result.is_valid is True
            assert calc.operation == Operation(op)
            calc.reset()

    def test_select_invalid_operation(self):
        """Test selecting invalid operation."""
        calc = CalculatorUI()
        result = calc.select_operation("invalid")
        assert result.is_valid is False
        assert "Invalid operation" in result.message
        assert calc.operation is None

    def test_select_empty_operation(self):
        """Test selecting empty operation."""
        calc = CalculatorUI()
        result = calc.select_operation("")
        assert result.is_valid is False
        assert "cannot be empty" in result.message

    def test_operation_case_insensitive(self):
        """Test operation selection is case insensitive."""
        calc = CalculatorUI()
        result = calc.select_operation("ADD")
        assert result.is_valid is True
        assert calc.operation == Operation.ADD


class TestCalculatorUICalculation:
    """Test CalculatorUI calculation functionality."""

    def test_calculate_addition(self):
        """Test addition calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 15.0
        assert "10.0 + 5.0 = 15.0" in result.expression

    def test_calculate_subtraction(self):
        """Test subtraction calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("subtract")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 5.0

    def test_calculate_multiplication(self):
        """Test multiplication calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("multiply")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 50.0

    def test_calculate_division(self):
        """Test division calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("divide")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 2.0

    def test_calculate_division_by_zero(self):
        """Test division by zero error."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("0")
        calc.select_operation("divide")
        result = calc.calculate()
        assert result.success is False
        assert result.result is None
        assert "Cannot divide by zero" in result.error_message

    def test_calculate_modulo(self):
        """Test modulo calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("17")
        calc.set_operand_b("5")
        calc.select_operation("modulo")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 2.0

    def test_calculate_power(self):
        """Test power calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("2")
        calc.set_operand_b("3")
        calc.select_operation("power")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 8.0

    def test_calculate_without_operand_a(self):
        """Test calculation without first operand."""
        calc = CalculatorUI()
        calc.set_operand_b("5")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is False
        assert "first number" in result.error_message

    def test_calculate_without_operand_b(self):
        """Test calculation without second operand."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is False
        assert "second number" in result.error_message

    def test_calculate_without_operation(self):
        """Test calculation without operation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        result = calc.calculate()
        assert result.success is False
        assert "select an operation" in result.error_message


class TestCalculatorUIHistory:
    """Test CalculatorUI history functionality."""

    def test_history_tracks_calculations(self):
        """Test that history tracks calculations."""
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("3")
        calc.select_operation("add")
        calc.calculate()
        assert len(calc.history) == 1

    def test_history_multiple_calculations(self):
        """Test history with multiple calculations."""
        calc = CalculatorUI()
        for i in range(5):
            calc.set_operand_a(str(i))
            calc.set_operand_b(str(i))
            calc.select_operation("add")
            calc.calculate()
        assert len(calc.history) == 5

    def test_clear_history(self):
        """Test clearing history."""
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("3")
        calc.select_operation("add")
        calc.calculate()
        calc.clear_history()
        assert len(calc.history) == 0

    def test_history_is_copy(self):
        """Test that history returns a copy."""
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("3")
        calc.select_operation("add")
        calc.calculate()
        history1 = calc.history
        history1.clear()
        assert len(calc.history) == 1  # Original unchanged


class TestCalculatorUIValidation:
    """Test CalculatorUI validation messaging."""

    def test_validation_messages_accumulate(self):
        """Test that validation messages accumulate."""
        calc = CalculatorUI()
        calc.set_operand_a("")
        calc.set_operand_b("")
        calc.select_operation("")
        assert len(calc.validation_messages) == 3

    def test_get_error_messages(self):
        """Test getting error messages."""
        calc = CalculatorUI()
        calc.set_operand_a("invalid")
        calc.set_operand_b("also_invalid")
        errors = calc.get_error_messages()
        assert len(errors) == 2
        assert all("must be a valid number" in msg for msg in errors)

    def test_clear_validation_messages(self):
        """Test clearing validation messages."""
        calc = CalculatorUI()
        calc.set_operand_a("invalid")
        calc.clear_validation_messages()
        assert len(calc.validation_messages) == 0


class TestCalculatorUIReset:
    """Test CalculatorUI reset functionality."""

    def test_reset_clears_operands(self):
        """Test reset clears operands."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.reset()
        assert calc.operand_a is None
        assert calc.operand_b is None

    def test_reset_clears_operation(self):
        """Test reset clears operation."""
        calc = CalculatorUI()
        calc.select_operation("add")
        calc.reset()
        assert calc.operation is None

    def test_reset_clears_validation_messages(self):
        """Test reset clears validation messages."""
        calc = CalculatorUI()
        calc.set_operand_a("invalid")
        calc.reset()
        assert len(calc.validation_messages) == 0


class TestCalculatorUIDisplay:
    """Test CalculatorUI display functionality."""

    def test_get_display_result_empty(self):
        """Test display result when no calculations."""
        calc = CalculatorUI()
        display = calc.get_display_result()
        assert "No calculations yet" in display

    def test_get_display_result_success(self):
        """Test display result after successful calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("5")
        calc.select_operation("add")
        calc.calculate()
        display = calc.get_display_result()
        assert "Result: 15.0" in display

    def test_get_display_result_error(self):
        """Test display result after failed calculation."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("0")
        calc.select_operation("divide")
        calc.calculate()
        display = calc.get_display_result()
        assert "Error:" in display
        assert "Cannot divide by zero" in display


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_numbers(self):
        """Test calculation with very large numbers."""
        calc = CalculatorUI()
        calc.set_operand_a("1e100")
        calc.set_operand_b("1e100")
        calc.select_operation("multiply")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 1e200

    def test_very_small_numbers(self):
        """Test calculation with very small numbers."""
        calc = CalculatorUI()
        calc.set_operand_a("1e-100")
        calc.set_operand_b("1e-100")
        calc.select_operation("add")
        result = calc.calculate()
        assert result.success is True

    def test_whitespace_in_input(self):
        """Test that whitespace is handled correctly."""
        calc = CalculatorUI()
        result = calc.set_operand_a("  10  ")
        assert result.is_valid is True
        assert calc.operand_a == 10.0

    def test_zero_power(self):
        """Test any number to power 0."""
        calc = CalculatorUI()
        calc.set_operand_a("5")
        calc.set_operand_b("0")
        calc.select_operation("power")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 1.0

    def test_negative_power(self):
        """Test negative exponent."""
        calc = CalculatorUI()
        calc.set_operand_a("2")
        calc.set_operand_b("-2")
        calc.select_operation("power")
        result = calc.calculate()
        assert result.success is True
        assert result.result == 0.25

    def test_modulo_by_zero(self):
        """Test modulo by zero error."""
        calc = CalculatorUI()
        calc.set_operand_a("10")
        calc.set_operand_b("0")
        calc.select_operation("modulo")
        result = calc.calculate()
        assert result.success is False
        assert "zero" in result.error_message.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
