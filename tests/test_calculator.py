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


# ============================================================
# Test validate_number
# ============================================================


class TestValidateNumber:
    """Tests for input number validation."""

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

    def test_valid_negative_scientific_notation(self):
        assert validate_number("-1.5e3") == -1500.0

    def test_valid_string_with_spaces(self):
        with pytest.raises(ValidationError):
            validate_number("  ")

    def test_none_raises_error(self):
        with pytest.raises(ValidationError, match="cannot be None"):
            validate_number(None)

    def test_boolean_true_raises_error(self):
        with pytest.raises(ValidationError, match="Boolean values"):
            validate_number(True)

    def test_boolean_false_raises_error(self):
        with pytest.raises(ValidationError, match="Boolean values"):
            validate_number(False)

    def test_invalid_string_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot convert"):
            validate_number("abc")

    def test_empty_string_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot convert"):
            validate_number("")

    def test_nan_raises_error(self):
        with pytest.raises(ValidationError, match="NaN values"):
            validate_number(float("nan"))

    def test_positive_infinity_raises_error(self):
        with pytest.raises(ValidationError, match="Infinite values"):
            validate_number(float("inf"))

    def test_negative_infinity_raises_error(self):
        with pytest.raises(ValidationError, match="Infinite values"):
            validate_number(float("-inf"))

    def test_value_too_large_raises_error(self):
        with pytest.raises(NumericOverflowError):
            validate_number(MAX_VALUE + 1)

    def test_value_too_small_raises_error(self):
        with pytest.raises(NumericOverflowError):
            validate_number(MIN_VALUE - 1)

    def test_boundary_max(self):
        assert validate_number(MAX_VALUE) == MAX_VALUE

    def test_boundary_min(self):
        assert validate_number(MIN_VALUE) == MIN_VALUE

    def test_list_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot convert"):
            validate_number([1, 2])

    def test_dict_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot convert"):
            validate_number({"a": 1})


# ============================================================
# Test validate_operation
# ============================================================


class TestValidateOperation:
    """Tests for operation string validation."""

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

    def test_case_insensitive_upper(self):
        assert validate_operation("ADD") == OperationType.ADD

    def test_case_insensitive_mixed(self):
        assert validate_operation("Add") == OperationType.ADD
        assert validate_operation("aDd") == OperationType.ADD

    def test_whitespace_stripped(self):
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

    def test_unsupported_shorthand_raises_error(self):
        with pytest.raises(ValidationError, match="Invalid operation"):
            validate_operation("sqrt")

    def test_list_raises_error(self):
        with pytest.raises(ValidationError, match="must be a string"):
            validate_operation(["add"])


# ============================================================
# Test validate_operands
# ============================================================


class TestValidateOperands:
    """Tests for operand list validation."""

    def test_valid_two_operands(self):
        result = validate_operands([1, 2], required_count=2)
        assert result == [1.0, 2.0]

    def test_valid_single_operand(self):
        result = validate_operands([16], required_count=1, allow_single=True)
        assert result == [16.0]

    def test_valid_string_operands(self):
        result = validate_operands(["10", "5"], required_count=2)
        assert result == [10.0, 5.0]

    def test_valid_tuple_operands(self):
        result = validate_operands((3, 4), required_count=2)
        assert result == [3.0, 4.0]

    def test_none_list_raises_error(self):
        with pytest.raises(MissingOperandError, match="cannot be None"):
            validate_operands(None)

    def test_string_raises_error(self):
        with pytest.raises(ValidationError, match="must be provided as a list"):
            validate_operands("1, 2")

    def test_int_raises_error(self):
        with pytest.raises(ValidationError, match="must be provided as a list"):
            validate_operands(42)

    def test_too_few_operands_raises_error(self):
        with pytest.raises(MissingOperandError, match="At least.*required"):
            validate_operands([1], required_count=2)

    def test_too_many_operands_raises_error(self):
        with pytest.raises(ValidationError, match="Expected exactly.*operands"):
            validate_operands([1, 2, 3], required_count=2)

    def test_invalid_operand_at_index(self):
        with pytest.raises(ValidationError, match="Invalid operand at index 1"):
            validate_operands([1, "invalid"])

    def test_empty_list_raises_error(self):
        with pytest.raises(MissingOperandError, match="At least.*required"):
            validate_operands([], required_count=1)

    def test_none_operand_in_list(self):
        with pytest.raises(ValidationError, match="Invalid operand at index 0"):
            validate_operands([None, 5])


# ============================================================
# Test add
# ============================================================


class TestAdd:
    """Tests for addition operation."""

    def test_positive_numbers(self):
        assert add(5, 3) == 8.0

    def test_negative_numbers(self):
        assert add(-5, -3) == -8.0

    def test_mixed_sign(self):
        assert add(-5, 3) == -2.0
        assert add(5, -3) == 2.0

    def test_zeros(self):
        assert add(0, 0) == 0.0

    def test_floats(self):
        assert add(1.5, 2.5) == 4.0

    def test_float_precision(self):
        assert add(0.1, 0.2) == pytest.approx(0.3)

    def test_string_operands(self):
        assert add("10", "5") == 15.0

    def test_invalid_first_operand(self):
        with pytest.raises(ValidationError):
            add("abc", 5)

    def test_invalid_second_operand(self):
        with pytest.raises(ValidationError):
            add(5, "xyz")

    def test_none_operand(self):
        with pytest.raises(ValidationError):
            add(None, 5)

    def test_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            add(MAX_VALUE, 1)

    def test_negative_overflow(self):
        with pytest.raises(NumericOverflowError):
            add(-MAX_VALUE, -1)

    def test_boundary_ok(self):
        assert add(MAX_VALUE - 1, 1) == MAX_VALUE

    def test_large_positive(self):
        assert add(1e14, 1e14) == 2e14


# ============================================================
# Test subtract
# ============================================================


class TestSubtract:
    """Tests for subtraction operation."""

    def test_positive_numbers(self):
        assert subtract(10, 3) == 7.0

    def test_negative_result(self):
        assert subtract(3, 10) == -7.0

    def test_both_negative(self):
        assert subtract(-10, -3) == -7.0

    def test_zeros(self):
        assert subtract(0, 0) == 0.0

    def test_floats(self):
        assert subtract(5.5, 2.5) == 3.0

    def test_float_precision(self):
        assert subtract(1.0, 0.9) == pytest.approx(0.1)

    def test_string_operands(self):
        assert subtract("10", "3") == 7.0

    def test_invalid_operand(self):
        with pytest.raises(ValidationError):
            subtract(None, 5)

    def test_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            subtract(-MAX_VALUE, 1)

    def test_boundary_ok(self):
        assert subtract(MIN_VALUE + 1, 1) == MIN_VALUE


# ============================================================
# Test multiply
# ============================================================


class TestMultiply:
    """Tests for multiplication operation."""

    def test_positive_numbers(self):
        assert multiply(5, 3) == 15.0

    def test_by_zero(self):
        assert multiply(5, 0) == 0.0
        assert multiply(0, 100) == 0.0

    def test_negative_numbers(self):
        assert multiply(-5, -3) == 15.0

    def test_mixed_sign(self):
        assert multiply(-5, 3) == -15.0

    def test_floats(self):
        assert multiply(2.5, 4) == 10.0

    def test_string_operands(self):
        assert multiply("6", "7") == 42.0

    def test_invalid_operand(self):
        with pytest.raises(ValidationError):
            multiply("abc", 5)

    def test_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            multiply(MAX_VALUE, 2)

    def test_one_is_identity(self):
        assert multiply(7, 1) == 7.0
        assert multiply(1, 7) == 7.0


# ============================================================
# Test divide
# ============================================================


class TestDivide:
    """Tests for division operation."""

    def test_positive_numbers(self):
        assert divide(10, 2) == 5.0

    def test_float_result(self):
        assert divide(7, 2) == 3.5

    def test_negative_numbers(self):
        assert divide(-10, -2) == 5.0
        assert divide(-10, 2) == -5.0

    def test_zero_dividend(self):
        assert divide(0, 5) == 0.0

    def test_divide_by_zero_raises_error(self):
        with pytest.raises(DivisionByZeroError, match="Cannot divide by zero"):
            divide(10, 0)

    def test_divide_negative_by_zero(self):
        with pytest.raises(DivisionByZeroError, match="Cannot divide by zero"):
            divide(-5, 0)

    def test_string_operands(self):
        assert divide("20", "4") == 5.0

    def test_invalid_operand(self):
        with pytest.raises(ValidationError):
            divide("invalid", 5)

    def test_none_operand(self):
        with pytest.raises(ValidationError):
            divide(None, 5)

    def test_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            divide(MAX_VALUE, 0.5)

    def test_fractional_result(self):
        assert divide(1, 3) == pytest.approx(0.3333333333333333)


# ============================================================
# Test modulo
# ============================================================


class TestModulo:
    """Tests for modulo operation."""

    def test_positive_numbers(self):
        assert modulo(10, 3) == 1.0

    def test_exact_division(self):
        assert modulo(10, 5) == 0.0

    def test_negative_dividend(self):
        assert modulo(-10, 3) == pytest.approx((-10) % 3)

    def test_floats(self):
        assert modulo(7.5, 2.5) == 0.0

    def test_zero_divisor_raises_error(self):
        with pytest.raises(DivisionByZeroError):
            modulo(10, 0)

    def test_string_operands(self):
        assert modulo("10", "3") == 1.0

    def test_invalid_operand(self):
        with pytest.raises(ValidationError):
            modulo("abc", 3)


# ============================================================
# Test power
# ============================================================


class TestPower:
    """Tests for power (exponentiation) operation."""

    def test_positive_exponent(self):
        assert power(2, 3) == 8.0

    def test_zero_exponent(self):
        assert power(5, 0) == 1.0

    def test_negative_exponent(self):
        assert power(2, -2) == 0.25

    def test_negative_base_integer_exponent(self):
        assert power(-2, 3) == -8.0
        assert power(-2, 2) == 4.0

    def test_fractional_exponent(self):
        assert power(4, 0.5) == pytest.approx(2.0)

    def test_zero_base_negative_exponent_raises_error(self):
        with pytest.raises(ValidationError, match="Cannot raise 0 to a negative power"):
            power(0, -1)

    def test_negative_base_fractional_exponent_raises_error(self):
        with pytest.raises(
            ValidationError, match="Cannot raise negative number to fractional power"
        ):
            power(-4, 0.5)

    def test_overflow_raises_error(self):
        with pytest.raises(NumericOverflowError):
            power(MAX_VALUE, 2)

    def test_string_operands(self):
        assert power("2", "3") == 8.0

    def test_invalid_operand(self):
        with pytest.raises(ValidationError):
            power("abc", 2)

    def test_one_is_identity(self):
        assert power(1, 100) == 1.0

    def test_base_one_any_exponent(self):
        assert power(1, -5) == 1.0
        assert power(1, 0.5) == 1.0


# ============================================================
# Test square_root
# ============================================================


class TestSquareRoot:
    """Tests for square root operation."""

    def test_perfect_square(self):
        assert square_root(16) == 4.0
        assert square_root(100) == 10.0

    def test_non_perfect_square(self):
        assert square_root(2) == pytest.approx(math.sqrt(2))

    def test_zero(self):
        assert square_root(0) == 0.0

    def test_one(self):
        assert square_root(1) == 1.0

    def test_float(self):
        assert square_root(6.25) == 2.5

    def test_negative_raises_error(self):
        with pytest.raises(
            ValidationError, match="Cannot compute square root of negative number"
        ):
            square_root(-4)

    def test_invalid_operand(self):
        with pytest.raises(ValidationError):
            square_root("invalid")

    def test_none_raises_error(self):
        with pytest.raises(ValidationError):
            square_root(None)

    def test_string_operand(self):
        assert square_root("25") == 5.0


# ============================================================
# Test calculate (unified interface)
# ============================================================


class TestCalculate:
    """Tests for the unified calculate function."""

    def test_add(self):
        assert calculate("add", [5, 3]) == 8.0

    def test_subtract(self):
        assert calculate("subtract", [10, 3]) == 7.0

    def test_multiply(self):
        assert calculate("multiply", [5, 3]) == 15.0

    def test_divide(self):
        assert calculate("divide", [10, 2]) == 5.0

    def test_modulo(self):
        assert calculate("modulo", [10, 3]) == 1.0

    def test_power(self):
        assert calculate("power", [2, 3]) == 8.0

    def test_square_root(self):
        assert calculate("square_root", [16]) == 4.0

    def test_case_insensitive(self):
        assert calculate("ADD", [5, 3]) == 8.0
        assert calculate("Divide", [10, 2]) == 5.0

    def test_invalid_operation_raises_error(self):
        with pytest.raises(ValidationError):
            calculate("invalid", [1, 2])

    def test_missing_operands_raises_error(self):
        with pytest.raises(MissingOperandError):
            calculate("add", [5])

    def test_too_many_operands_raises_error(self):
        with pytest.raises(ValidationError):
            calculate("add", [1, 2, 3])

    def test_division_by_zero_raises_error(self):
        with pytest.raises(DivisionByZeroError):
            calculate("divide", [10, 0])

    def test_invalid_operand_raises_error(self):
        with pytest.raises(ValidationError):
            calculate("add", [5, "invalid"])

    def test_none_operation_raises_error(self):
        with pytest.raises(ValidationError):
            calculate(None, [1, 2])

    def test_none_operands_raises_error(self):
        with pytest.raises(MissingOperandError):
            calculate("add", None)

    def test_empty_operands_raises_error(self):
        with pytest.raises(MissingOperandError):
            calculate("add", [])

    def test_square_root_ignores_extra_operands(self):
        result = calculate("square_root", [16, 4])
        assert result == 4.0

    def test_whitespace_operation(self):
        assert calculate("  add  ", [2, 3]) == 5.0

    def test_string_operands_in_calculate(self):
        assert calculate("multiply", ["4", "5"]) == 20.0


# ============================================================
# Test calculate_safe (safe wrapper)
# ============================================================


class TestCalculateSafe:
    """Tests for the safe calculate wrapper."""

    def test_success(self):
        result = calculate_safe("add", [5, 3])
        assert result.success is True
        assert result.result == 8.0
        assert result.error is None
        assert result.operation == "add"
        assert result.operands == (5, 3)

    def test_division_by_zero_returns_failure(self):
        result = calculate_safe("divide", [10, 0])
        assert result.success is False
        assert result.result is None
        assert "divide by zero" in result.error.lower()

    def test_invalid_operation_returns_failure(self):
        result = calculate_safe("invalid", [1, 2])
        assert result.success is False
        assert result.result is None
        assert "invalid operation" in result.error.lower()

    def test_invalid_operands_returns_failure(self):
        result = calculate_safe("add", [5, "invalid"])
        assert result.success is False
        assert result.result is None
        assert "invalid operand" in result.error.lower()

    def test_none_operation_returns_failure(self):
        result = calculate_safe(None, [1, 2])
        assert result.success is False
        assert result.error is not None

    def test_none_operands_returns_failure(self):
        result = calculate_safe("add", None)
        assert result.success is False
        assert result.error is not None

    def test_to_dict(self):
        result = calculate_safe("add", [5, 3])
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["success"] is True
        assert d["result"] == 8.0
        assert d["error"] is None
        assert d["operation"] == "add"
        assert d["operands"] == (5, 3)

    def test_to_dict_failure(self):
        result = calculate_safe("divide", [10, 0])
        d = result.to_dict()
        assert d["success"] is False
        assert d["result"] is None
        assert d["error"] is not None

    def test_square_root_success(self):
        result = calculate_safe("square_root", [25])
        assert result.success is True
        assert result.result == 5.0


# ============================================================
# Test CalculationResult dataclass
# ============================================================


class TestCalculationResult:
    """Tests for the CalculationResult dataclass."""

    def test_successful_result(self):
        result = CalculationResult(
            success=True, result=42.0, operation="add", operands=(1, 2)
        )
        assert result.success is True
        assert result.result == 42.0
        assert result.error is None
        assert result.operation == "add"
        assert result.operands == (1, 2)

    def test_failed_result(self):
        result = CalculationResult(
            success=False, error="Division by zero", operation="divide", operands=(1, 0)
        )
        assert result.success is False
        assert result.result is None
        assert result.error == "Division by zero"

    def test_to_dict_success(self):
        result = CalculationResult(
            success=True, result=42.0, operation="add", operands=(1, 2)
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["result"] == 42.0
        assert d["error"] is None
        assert d["operation"] == "add"
        assert d["operands"] == (1, 2)

    def test_to_dict_failure(self):
        result = CalculationResult(
            success=False, error="Test error", operation="test", operands=(1, 2)
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["result"] is None
        assert d["error"] == "Test error"

    def test_defaults(self):
        result = CalculationResult(success=True)
        assert result.result is None
        assert result.error is None
        assert result.operation is None
        assert result.operands is None


# ============================================================
# Test error class hierarchy
# ============================================================


class TestErrorClasses:
    """Tests for custom exception hierarchy."""

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

    def test_all_errors_are_exceptions(self):
        assert issubclass(CalculatorError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(DivisionByZeroError, Exception)

    def test_calculator_error_can_be_raised(self):
        with pytest.raises(CalculatorError):
            raise CalculatorError("test")

    def test_error_messages(self):
        err = ValidationError("test message")
        assert str(err) == "test message"


# ============================================================
# Test OperationType enum
# ============================================================


class TestOperationType:
    """Tests for OperationType enum."""

    def test_all_operations_exist(self):
        expected = {
            "add",
            "subtract",
            "multiply",
            "divide",
            "modulo",
            "power",
            "square_root",
        }
        actual = {op.value for op in OperationType}
        assert actual == expected

    def test_enum_values(self):
        assert OperationType.ADD.value == "add"
        assert OperationType.SUBTRACT.value == "subtract"
        assert OperationType.MULTIPLY.value == "multiply"
        assert OperationType.DIVIDE.value == "divide"
        assert OperationType.MODULO.value == "modulo"
        assert OperationType.POWER.value == "power"
        assert OperationType.SQUARE_ROOT.value == "square_root"


# ============================================================
# Test edge cases and boundary conditions
# ============================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_max_boundary_addition(self):
        result = add(MAX_VALUE - 1, 1)
        assert result == MAX_VALUE

    def test_min_boundary_subtraction(self):
        result = subtract(MIN_VALUE + 1, 1)
        assert result == MIN_VALUE

    def test_very_small_numbers(self):
        result = add(1e-15, 1e-15)
        assert result == pytest.approx(2e-15)

    def test_zero_operations(self):
        assert add(0, 0) == 0
        assert subtract(0, 0) == 0
        assert multiply(0, 0) == 0
        assert power(0, 0) == 1  # math convention

    def test_divide_very_small_by_large(self):
        result = divide(1e-10, 1e10)
        assert result == pytest.approx(1e-20)

    def test_power_large_base_small_exponent(self):
        result = power(1e5, 2)
        assert result == pytest.approx(1e10)

    def test_modulo_with_floats(self):
        result = modulo(5.5, 2.5)
        assert result == pytest.approx(0.5)

    def test_negative_zero(self):
        assert add(-0.0, 0.0) == 0.0
        assert validate_number(-0.0) == 0.0

    def test_calculate_safe_with_large_numbers(self):
        result = calculate_safe("add", [MAX_VALUE - 1, 1])
        assert result.success is True
        assert result.result == MAX_VALUE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
