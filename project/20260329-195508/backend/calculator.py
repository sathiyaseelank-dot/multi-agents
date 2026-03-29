"""Core calculator module with basic arithmetic operations and validation."""

from typing import Union, Tuple, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import math


class OperationType(Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    MODULO = "modulo"
    POWER = "power"
    SQUARE_ROOT = "square_root"


@dataclass
class CalculationResult:
    success: bool
    result: Optional[float] = None
    error: Optional[str] = None
    operation: Optional[str] = None
    operands: Optional[Tuple[float, ...]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "operation": self.operation,
            "operands": self.operands,
        }


class CalculatorError(Exception):
    pass


class ValidationError(CalculatorError):
    pass


class DivisionByZeroError(CalculatorError):
    pass


class NumericOverflowError(CalculatorError):
    pass


class MissingOperandError(CalculatorError):
    pass


class UnsupportedOperationError(CalculatorError):
    pass


MAX_VALUE = 1e15
MIN_VALUE = -1e15


def validate_number(value: Any) -> float:
    """Validate and convert input to a valid number.
    
    Args:
        value: Input value to validate
        
    Returns:
        Validated float value
        
    Raises:
        ValidationError: If value cannot be converted to a valid number
    """
    if value is None:
        raise ValidationError("Input value cannot be None")
    
    if isinstance(value, bool):
        raise ValidationError("Boolean values are not valid numeric inputs")
    
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Cannot convert '{value}' to a number")
    
    if math.isnan(num):
        raise ValidationError("NaN values are not allowed")
    
    if math.isinf(num):
        raise ValidationError("Infinite values are not allowed")
    
    if not MIN_VALUE <= num <= MAX_VALUE:
        raise NumericOverflowError(f"Number must be between {MIN_VALUE} and {MAX_VALUE}")
    
    return num


def validate_operation(operation: str) -> OperationType:
    """Validate operation string and return OperationType enum.
    
    Args:
        operation: Operation string to validate
        
    Returns:
        Valid OperationType enum value
        
    Raises:
        ValidationError: If operation is not valid
    """
    if operation is None:
        raise ValidationError("Operation cannot be None")
    
    if not isinstance(operation, str):
        raise ValidationError("Operation must be a string")
    
    if not operation.strip():
        raise ValidationError("Operation cannot be empty or whitespace")
    
    operation_lower = operation.lower().strip()
    
    try:
        return OperationType(operation_lower)
    except ValueError:
        valid_ops = [op.value for op in OperationType]
        raise ValidationError(
            f"Invalid operation '{operation}'. Valid operations: {valid_ops}"
        )


def validate_operands(
    operands: List[Any], 
    required_count: int = 2,
    allow_single: bool = False
) -> List[float]:
    """Validate a list of operands.
    
    Args:
        operands: List of operands to validate
        required_count: Minimum number of operands required
        allow_single: Whether to allow single operand operations
        
    Returns:
        List of validated float operands
        
    Raises:
        MissingOperandError: If not enough operands provided
        ValidationError: If operands are invalid
    """
    if operands is None:
        raise MissingOperandError("Operands list cannot be None")
    
    if not isinstance(operands, (list, tuple)):
        raise ValidationError("Operands must be provided as a list or tuple")
    
    if len(operands) < required_count:
        raise MissingOperandError(
            f"At least {required_count} operand(s) required, got {len(operands)}"
        )
    
    if not allow_single and len(operands) != required_count:
        raise ValidationError(
            f"Expected exactly {required_count} operands, got {len(operands)}"
        )
    
    validated = []
    for i, operand in enumerate(operands):
        try:
            validated.append(validate_number(operand))
        except ValidationError as e:
            raise ValidationError(f"Invalid operand at index {i}: {str(e)}")
    
    return validated


def add(a: float, b: float) -> float:
    """Add two numbers.
    
    Args:
        a: First operand
        b: Second operand
        
    Returns:
        Sum of a and b
        
    Raises:
        ValidationError: If inputs are invalid
        NumericOverflowError: If result exceeds allowed range
    """
    a_val = validate_number(a)
    b_val = validate_number(b)
    
    result = a_val + b_val
    
    if not MIN_VALUE <= result <= MAX_VALUE:
        raise NumericOverflowError("Addition result exceeds allowed range")
    
    return result


def subtract(a: float, b: float) -> float:
    """Subtract second number from first.
    
    Args:
        a: First operand
        b: Second operand
        
    Returns:
        Difference of a and b
        
    Raises:
        ValidationError: If inputs are invalid
        NumericOverflowError: If result exceeds allowed range
    """
    a_val = validate_number(a)
    b_val = validate_number(b)
    
    result = a_val - b_val
    
    if not MIN_VALUE <= result <= MAX_VALUE:
        raise NumericOverflowError("Subtraction result exceeds allowed range")
    
    return result


def multiply(a: float, b: float) -> float:
    """Multiply two numbers.
    
    Args:
        a: First operand
        b: Second operand
        
    Returns:
        Product of a and b
        
    Raises:
        ValidationError: If inputs are invalid
        NumericOverflowError: If result exceeds allowed range
    """
    a_val = validate_number(a)
    b_val = validate_number(b)
    
    result = a_val * b_val
    
    if not MIN_VALUE <= result <= MAX_VALUE:
        raise NumericOverflowError("Multiplication result exceeds allowed range")
    
    return result


def divide(a: float, b: float) -> float:
    """Divide first number by second.
    
    Args:
        a: Dividend
        b: Divisor
        
    Returns:
        Quotient of a and b
        
    Raises:
        ValidationError: If inputs are invalid
        DivisionByZeroError: If divisor is zero
        NumericOverflowError: If result exceeds allowed range
    """
    a_val = validate_number(a)
    b_val = validate_number(b)
    
    if b_val == 0:
        raise DivisionByZeroError("Cannot divide by zero")
    
    result = a_val / b_val
    
    if not MIN_VALUE <= result <= MAX_VALUE:
        raise NumericOverflowError("Division result exceeds allowed range")
    
    return result


def modulo(a: float, b: float) -> float:
    """Compute modulo of first number by second.
    
    Args:
        a: Dividend
        b: Divisor
        
    Returns:
        Remainder of a divided by b
        
    Raises:
        ValidationError: If inputs are invalid
        DivisionByZeroError: If divisor is zero
    """
    a_val = validate_number(a)
    b_val = validate_number(b)
    
    if b_val == 0:
        raise DivisionByZeroError("Cannot compute modulo with zero divisor")
    
    return a_val % b_val


def power(a: float, b: float) -> float:
    """Raise first number to the power of second.
    
    Args:
        a: Base
        b: Exponent
        
    Returns:
        a raised to the power of b
        
    Raises:
        ValidationError: If inputs are invalid
        NumericOverflowError: If result exceeds allowed range
    """
    a_val = validate_number(a)
    b_val = validate_number(b)
    
    if a_val == 0 and b_val < 0:
        raise ValidationError("Cannot raise 0 to a negative power")
    
    if a_val < 0 and not b_val.is_integer():
        raise ValidationError("Cannot raise negative number to fractional power")
    
    result = math.pow(a_val, b_val)
    
    if math.isnan(result):
        raise ValidationError("Power operation resulted in an invalid number")
    
    if math.isinf(result):
        raise NumericOverflowError("Power operation result exceeds allowed range")
    
    if not MIN_VALUE <= result <= MAX_VALUE:
        raise NumericOverflowError("Power operation result exceeds allowed range")
    
    return result


def square_root(a: float) -> float:
    """Compute square root of a number.
    
    Args:
        a: Number to compute square root of
        
    Returns:
        Square root of a
        
    Raises:
        ValidationError: If input is invalid or negative
    """
    a_val = validate_number(a)
    
    if a_val < 0:
        raise ValidationError("Cannot compute square root of negative number")
    
    result = math.sqrt(a_val)
    
    if not MIN_VALUE <= result <= MAX_VALUE:
        raise NumericOverflowError("Square root result exceeds allowed range")
    
    return result


def calculate(operation: str, operands: List[Any]) -> float:
    """Perform calculation with given operation and operands.
    
    Args:
        operation: Operation to perform
        operands: List of operands for the operation
        
    Returns:
        Result of the calculation
        
    Raises:
        ValidationError: If operation or operands are invalid
        DivisionByZeroError: If division by zero occurs
        NumericOverflowError: If result exceeds allowed range
        UnsupportedOperationError: If operation is not supported
    """
    op_type = validate_operation(operation)
    
    operations_map = {
        OperationType.ADD: (add, 2),
        OperationType.SUBTRACT: (subtract, 2),
        OperationType.MULTIPLY: (multiply, 2),
        OperationType.DIVIDE: (divide, 2),
        OperationType.MODULO: (modulo, 2),
        OperationType.POWER: (power, 2),
        OperationType.SQUARE_ROOT: (square_root, 1),
    }
    
    if op_type not in operations_map:
        raise UnsupportedOperationError(f"Operation '{operation}' is not supported")
    
    func, required_count = operations_map[op_type]
    
    if op_type == OperationType.SQUARE_ROOT:
        validated = validate_operands(operands, required_count=1, allow_single=True)
        return func(validated[0])
    else:
        validated = validate_operands(operands, required_count=required_count)
        return func(validated[0], validated[1])


def calculate_safe(operation: str, operands: List[Any]) -> CalculationResult:
    """Perform calculation with given operation and operands, returning a safe result.
    
    Args:
        operation: Operation to perform
        operands: List of operands for the operation
        
    Returns:
        CalculationResult with success status, result or error
    """
    try:
        result = calculate(operation, operands)
        return CalculationResult(
            success=True,
            result=result,
            operation=operation,
            operands=tuple(operands) if operands else None
        )
    except CalculatorError as e:
        return CalculationResult(
            success=False,
            error=str(e),
            operation=operation,
            operands=tuple(operands) if operands else None
        )
