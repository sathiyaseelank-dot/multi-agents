"""Comprehensive tests for the calculator module."""

import pytest
import math
from calculator import (
    add,
    subtract,
    multiply,
    divide,
    modulo,
    power,
    square_root,
    calculate,
    calculate_safe,
    validate_number,
    validate_operation,
    validate_operands,
    ValidationError,
    DivisionByZeroError,
    NumericOverflowError,
    MissingOperandError,
    UnsupportedOperationError,
    CalculatorError,
    OperationType,
    CalculationResult,
    MAX_VALUE,
    MIN_VALUE,
)


class TestValidateNumber:
    def test_valid_integer(self):
        assert validate_number(42) == 42.0
    
    def test_valid_float(self):
        assert validate_number(3.14) == 3.14
    
    def test_valid_string_number(self):
        assert validate_number("123") == 123.0
    
    def test_valid_negative_number(self):
        assert validate_number(-50) == -50.0
    
    def test_valid_zero(self):
        assert validate_number(0) == 0.0
    
    def test_valid_scientific_notation(self):
        assert validate_number("1e5") == 100000.0
    
    def test_none_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be None"):
            validate_number(None)
    
    def test_boolean_raises_error(self):
        with pytest.raises(ValidationError, match="Boolean values"):
            validate_number(True)
        with pytest.raises(ValidationError, match="Boolean values"):
            validate_number(False)
    
    def test_string_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot convert"):
            validate_number("abc")
    
    def test_nan_raises_error(self):
        with pytest.raises(ValidationError, match="NaN values"):
            validate_number(float("nan"))
    
    def test_infinity_raises_error(self):
        with pytest.raises(ValidationError, match="Infinite values"):
            validate_number(float("inf"))
    
    def test_negative_infinity_raises_error(self):
        with pytest.raises(ValidationError, match="Infinite values"):
            validate_number(float("-inf"))
    
    def test_value_too_large(self):
        with pytest.raises(NumericOverflowError):
            validate_number(MAX_VALUE + 1)
    
    def test_value_too_small(self):
        with pytest.raises(NumericOverflowError):
            validate_number(MIN_VALUE - 1)
    
    def test_boundary_max(self):
        assert validate_number(MAX_VALUE) == MAX_VALUE
    
    def test_boundary_min(self):
        assert validate_number(MIN_VALUE) == MIN_VALUE


class TestValidateOperation:
    def test_valid_add(self):
        assert validate_operation("add") == OperationType.ADD
    
    def test_valid_subtract(self):
        assert validate_operation("subtract") == OperationType.SUBTRACT
    
    def test_valid_multiply(self):
        assert validate_operation("multiply") == OperationType.MULTIPLY
    
    def test_valid_divide(self):
        assert validate_operation("divide") == OperationType.DIVIDE
    
    def test_valid_modulo(self):
        assert validate_operation("modulo") == OperationType.MODULO
    
    def test_valid_power(self):
        assert validate_operation("power") == OperationType.POWER
    
    def test_valid_square_root(self):
        assert validate_operation("square_root") == OperationType.SQUARE_ROOT
    
    def test_valid_case_insensitive(self):
        assert validate_operation("ADD") == OperationType.ADD
        assert validate_operation("Add") == OperationType.ADD
        assert validate_operation("aDd") == OperationType.ADD
    
    def test_valid_with_whitespace(self):
        assert validate_operation("  add  ") == OperationType.ADD
        assert validate_operation("\tdivide\t") == OperationType.DIVIDE
    
    def test_none_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be None"):
            validate_operation(None)
    
    def test_empty_string_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_operation("")
    
    def test_whitespace_only_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_operation("   ")
    
    def test_non_string_raises_error(self):
        with pytest.raises(ValidationError, match="must be a string"):
            validate_operation(123)
    
    def test_invalid_operation_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid operation"):
            validate_operation("invalid")
    
    def test_unsupported_operation_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid operation".lower()):
            validate_operation("sqrt")


class TestValidateOperands:
    def test_valid_two_operands(self):
        result = validate_operands([1, 2], required_count=2)
        assert result == [1.0, 2.0]
    
    def test_valid_single_operand(self):
        result = validate_operands([16], required_count=1, allow_single=True)
        assert result == [16.0]
    
    def test_valid_string_operands(self):
        result = validate_operands(["10", "5"], required_count=2)
        assert result == [10.0, 5.0]
    
    def test_none_list_raises_error(self):
        with pytest.raises(MissingOperandError, match="cannot be None"):
            validate_operands(None)
    
    def test_not_list_raises_error(self):
        with pytest.raises(ValidationError, match="must be provided as a list"):
            validate_operands("1, 2")
    
    def test_too_few_operands_raises_error(self):
        with pytest.raises(MissingOperandError, match="At least.*required"):
            validate_operands([1], required_count=2)
    
    def test_too_many_operands_raises_error(self):
        with pytest.raises(ValidationError, match="Expected exactly.*operands"):
            validate_operands([1, 2, 3], required_count=2)
    
    def test_invalid_operand_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid operand at index"):
            validate_operands([1, "invalid"])
    
    def test_empty_list_raises_error(self):
        with pytest.raises(MissingOperandError, match="At least.*required"):
            validate_operands([], required_count=1)


class TestAdd:
    def test_add_positive_numbers(self):
        assert add(5, 3) == 8.0
    
    def test_add_negative_numbers(self):
        assert add(-5, -3) == -8.0
    
    def test_add_mixed_numbers(self):
        assert add(-5, 3) == -2.0
    
    def test_add_zeros(self):
        assert add(0, 0) == 0.0
    
    def test_add_floats(self):
        assert add(1.5, 2.5) == 4.0
    
    def test_add_strings(self):
        assert add("10", "5") == 15.0
    
    def test_add_invalid_raises_error(self):
        with pytest.raises(ValidationError):
            add("abc", 5)
    
    def test_add_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            add(MAX_VALUE, 1)


class TestSubtract:
    def test_subtract_positive_numbers(self):
        assert subtract(10, 3) == 7.0
    
    def test_subtract_negative_numbers(self):
        assert subtract(-10, -3) == -7.0
    
    def test_subtract_mixed_numbers(self):
        assert subtract(-10, 3) == -13.0
    
    def test_subtract_zeros(self):
        assert subtract(0, 0) == 0.0
    
    def test_subtract_floats(self):
        assert subtract(5.5, 2.5) == 3.0
    
    def test_invalid_raises_error(self):
        with pytest.raises(ValidationError):
            subtract(None, 5)


class TestMultiply:
    def test_multiply_positive_numbers(self):
        assert multiply(5, 3) == 15.0
    
    def test_multiply_by_zero(self):
        assert multiply(5, 0) == 0.0
    
    def test_multiply_negative_numbers(self):
        assert multiply(-5, -3) == 15.0
    
    def test_multiply_floats(self):
        assert multiply(2.5, 4) == 10.0
    
    def test_multiply_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            multiply(MAX_VALUE, 2)


class TestDivide:
    def test_divide_positive_numbers(self):
        assert divide(10, 2) == 5.0
    
    def test_divide_floats(self):
        assert divide(7, 2) == 3.5
    
    def test_divide_negative_numbers(self):
        assert divide(-10, -2) == 5.0
    
    def test_divide_by_zero_raises_error(self):
        with pytest.raises(DivisionByZeroError, match="Cannot divide by zero"):
            divide(10, 0)
    
    def test_divide_zero_by_number(self):
        assert divide(0, 5) == 0.0
    
    def test_divide_invalid_raises_error(self):
        with pytest.raises(ValidationError):
            divide("invalid", 5)


class TestModulo:
    def test_modulo_positive_numbers(self):
        assert modulo(10, 3) == 1.0
    
    def test_modulo_zero_raises_error(self):
        with pytest.raises(DivisionByZeroError):
            modulo(10, 0)
    
    def test_modulo_negative_numbers(self):
        assert modulo(-10, 3) == -1.0
    
    def test_modulo_floats(self):
        assert modulo(7.5, 2.5) == 0.0


class TestPower:
    def test_power_positive_exponent(self):
        assert power(2, 3) == 8.0
    
    def test_power_zero_exponent(self):
        assert power(5, 0) == 1.0
    
    def test_power_negative_exponent(self):
        assert power(2, -2) == 0.25
    
    def test_power_zero_base_negative_exponent_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot raise 0 to a negative power"):
            power(0, -1)
    
    def test_power_negative_base_fractional_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot raise negative number to fractional power"):
            power(-4, 0.5)
    
    def test_power_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            power(MAX_VALUE, 2)


class TestSquareRoot:
    def test_square_root_positive_number(self):
        assert square_root(16) == 4.0
    
    def test_square_root_zero(self):
        assert square_root(0) == 0.0
    
    def test_square_root_one(self):
        assert square_root(1) == 1.0
    
    def test_square_root_float(self):
        assert square_root(2) == pytest.approx(math.sqrt(2))
    
    def test_square_root_negative_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot compute square root of negative number"):
            square_root(-4)
    
    def test_square_root_invalid_raises_error(self):
        with pytest.raises(ValidationError):
            square_root("invalid")


class TestCalculate:
    def test_calculate_add(self):
        assert calculate("add", [5, 3]) == 8.0
    
    def test_calculate_subtract(self):
        assert calculate("subtract", [10, 3]) == 7.0
    
    def test_calculate_multiply(self):
        assert calculate("multiply", [5, 3]) == 15.0
    
    def test_calculate_divide(self):
        assert calculate("divide", [10, 2]) == 5.0
    
    def test_calculate_modulo(self):
        assert calculate("modulo", [10, 3]) == 1.0
    
    def test_calculate_power(self):
        assert calculate("power", [2, 3]) == 8.0
    
    def test_calculate_square_root(self):
        assert calculate("square_root", [16]) == 4.0
    
    def test_calculate_invalid_operation_raises_error(self):
        with pytest.raises(ValidationError):
            calculate("invalid", [1, 2])
    
    def test_calculate_missing_operands_raises_error(self):
        with pytest.raises(MissingOperandError):
            calculate("add", [5])
    
    def test_calculate_division_by_zero_raises_error(self):
        with pytest.raises(DivisionByZeroError):
            calculate("divide", [10, 0])
    
    def test_calculate_invalid_operand_raises_error(self):
        with pytest.raises(ValidationError):
            calculate("add", [5, "invalid"])


class TestCalculateSafe:
    def test_calculate_safe_success(self):
        result = calculate_safe("add", [5, 3])
        assert result.success is True
        assert result.result == 8.0
        assert result.error is None
        assert result.operation == "add"
    
    def test_calculate_safe_division_by_zero(self):
        result = calculate_safe("divide", [10, 0])
        assert result.success is False
        assert result.result is None
        assert "divide by zero" in result.error.lower()
    
    def test_calculate_safe_invalid_operation(self):
        result = calculate_safe("invalid", [1, 2])
        assert result.success is False
        assert result.result is None
        assert "invalid operation" in result.error.lower()
    
    def test_calculate_safe_invalid_operands(self):
        result = calculate_safe("add", [5, "invalid"])
        assert result.success is False
        assert result.result is None
        assert "invalid operand" in result.error.lower()
    
    def test_calculate_safe_to_dict(self):
        result = calculate_safe("add", [5, 3])
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["result"] == 8.0


class TestEdgeCases:
    def test_max_boundary_addition(self):
        result = add(MAX_VALUE - 1, 1)
        assert result == MAX_VALUE
    
    def test_min_boundary_subtraction(self):
        result = subtract(MIN_VALUE + 1, 1)
        assert result == MIN_VALUE
    
    def test_precision_with_large_numbers(self):
        result = add(1e14, 1e14)
        assert result == 2e14
    
    def test_precision_with_small_numbers(self):
        result = add(0.1, 0.2)
        assert result == pytest.approx(0.3, rel=1e-10)
    
    def test_empty_operands_list(self):
        with pytest.raises(MissingOperandError):
            validate_operands([])


class TestErrorClasses:
    def test_validation_error_is_calculator_error(self):
        assert issubclass(ValidationError, CalculatorError)
    
    def test_division_by_zero_error_is_calculator_error(self):
        assert issubclass(DivisionByZeroError, CalculatorError)
    
    def test_numeric_overflow_error_is_calculator_error(self):
        assert issubclass(NumericOverflowError, CalculatorError)
    
    def test_missing_operand_error_is_calculator_error(self):
        assert issubclass(MissingOperandError, CalculatorError)
    
    def test_unsupported_operation_error_is_calculator_error(self):
        assert issubclass(UnsupportedOperationError, CalculatorError)


class TestCalculationResult:
    def test_successful_result_to_dict(self):
        result = CalculationResult(
            success=True,
            result=42.0,
            operation="add",
            operands=(1, 2)
        )
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["result"] == 42.0
        assert result_dict["operation"] == "add"
        assert result_dict["operands"] == (1, 2)
        assert result_dict["error"] is None
    
    def test_failed_result_to_dict(self):
        result = CalculationResult(
            success=False,
            error="Division by zero",
            operation="divide",
            operands=(1, 0)
        )
        result_dict = result.to_dict()
        assert result_dict["success"] is False
        assert result_dict["result"] is None
        assert result_dict["error"] == "Division by zero"
