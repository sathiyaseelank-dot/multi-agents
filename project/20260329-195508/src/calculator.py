"""
Calculator module with user-facing UI components,
validation, and operation handling.
"""

from typing import Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass


class Operation(Enum):
    """Supported calculator operations."""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    MODULO = "modulo"
    POWER = "power"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    message: str
    field: Optional[str] = None


@dataclass
class CalculationResult:
    """Result of a calculation operation."""
    success: bool
    result: Optional[float]
    expression: str
    error_message: Optional[str] = None


class CalculatorUI:
    """
    User-facing calculator UI with input controls,
    operation selection, result display, and validation.
    """

    def __init__(self):
        self._operand_a: Optional[float] = None
        self._operand_b: Optional[float] = None
        self._operation: Optional[Operation] = None
        self._history: List[CalculationResult] = []
        self._validation_messages: List[ValidationResult] = []

    @property
    def operand_a(self) -> Optional[float]:
        """Get first operand value."""
        return self._operand_a

    @property
    def operand_b(self) -> Optional[float]:
        """Get second operand value."""
        return self._operand_b

    @property
    def operation(self) -> Optional[Operation]:
        """Get selected operation."""
        return self._operation

    @property
    def history(self) -> List[CalculationResult]:
        """Get calculation history."""
        return self._history.copy()

    @property
    def validation_messages(self) -> List[ValidationResult]:
        """Get validation messages."""
        return self._validation_messages.copy()

    def clear_validation_messages(self) -> None:
        """Clear all validation messages."""
        self._validation_messages.clear()

    def set_operand_a(self, value: str) -> ValidationResult:
        """
        Set first operand from string input.
        
        Args:
            value: String representation of the number
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = self._validate_number(value, "Operand A")
        if result.is_valid:
            self._operand_a = float(value)
        self._validation_messages.append(result)
        return result

    def set_operand_b(self, value: str) -> ValidationResult:
        """
        Set second operand from string input.
        
        Args:
            value: String representation of the number
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = self._validate_number(value, "Operand B")
        if result.is_valid:
            self._operand_b = float(value)
        self._validation_messages.append(result)
        return result

    def select_operation(self, operation: str) -> ValidationResult:
        """
        Select calculator operation.
        
        Args:
            operation: Operation name (add, subtract, multiply, divide, modulo, power)
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = self._validate_operation(operation)
        if result.is_valid:
            self._operation = Operation(operation.lower())
        self._validation_messages.append(result)
        return result

    def calculate(self) -> CalculationResult:
        """
        Perform calculation with current operands and operation.
        
        Returns:
            CalculationResult with success status and result or error
        """
        # Validate inputs before calculation
        validation = self._validate_calculation()
        if not validation.is_valid:
            self._validation_messages.append(validation)
            return CalculationResult(
                success=False,
                result=None,
                expression="",
                error_message=validation.message
            )

        # Perform the calculation
        try:
            result = self._execute_operation()
            expression = self._build_expression(result)
            
            calc_result = CalculationResult(
                success=True,
                result=result,
                expression=expression
            )
            self._history.append(calc_result)
            return calc_result
            
        except ValueError as e:
            error_result = CalculationResult(
                success=False,
                result=None,
                expression=self._build_expression(0),
                error_message=str(e)
            )
            self._history.append(error_result)
            return error_result

    def reset(self) -> None:
        """Reset calculator state."""
        self._operand_a = None
        self._operand_b = None
        self._operation = None
        self.clear_validation_messages()

    def clear_history(self) -> None:
        """Clear calculation history."""
        self._history.clear()

    def _validate_number(self, value: str, field_name: str) -> ValidationResult:
        """
        Validate that a string is a valid number.
        
        Args:
            value: String to validate
            field_name: Name of the field for error messages
            
        Returns:
            ValidationResult with validation status
        """
        if not value or value.strip() == "":
            return ValidationResult(
                is_valid=False,
                message=f"{field_name} cannot be empty",
                field=field_name
            )
        
        try:
            float(value)
            return ValidationResult(
                is_valid=True,
                message=f"{field_name} is valid",
                field=field_name
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                message=f"{field_name} must be a valid number",
                field=field_name
            )

    def _validate_operation(self, operation: str) -> ValidationResult:
        """
        Validate operation name.
        
        Args:
            operation: Operation name to validate
            
        Returns:
            ValidationResult with validation status
        """
        valid_operations = [op.value for op in Operation]
        
        if not operation or operation.strip() == "":
            return ValidationResult(
                is_valid=False,
                message="Operation cannot be empty",
                field="operation"
            )
        
        if operation.lower() not in valid_operations:
            return ValidationResult(
                is_valid=False,
                message=f"Invalid operation. Choose from: {', '.join(valid_operations)}",
                field="operation"
            )
        
        return ValidationResult(
            is_valid=True,
            message="Operation is valid",
            field="operation"
        )

    def _validate_calculation(self) -> ValidationResult:
        """
        Validate all inputs before calculation.
        
        Returns:
            ValidationResult with overall validation status
        """
        if self._operand_a is None:
            return ValidationResult(
                is_valid=False,
                message="Please enter the first number",
                field="operand_a"
            )
        
        if self._operand_b is None:
            return ValidationResult(
                is_valid=False,
                message="Please enter the second number",
                field="operand_b"
            )
        
        if self._operation is None:
            return ValidationResult(
                is_valid=False,
                message="Please select an operation",
                field="operation"
            )
        
        # Special validation for division
        if self._operation == Operation.DIVIDE and self._operand_b == 0:
            return ValidationResult(
                is_valid=False,
                message="Cannot divide by zero",
                field="operand_b"
            )
        
        return ValidationResult(
            is_valid=True,
            message="All inputs are valid"
        )

    def _execute_operation(self) -> float:
        """
        Execute the selected operation.
        
        Returns:
            Result of the operation
            
        Raises:
            ValueError: If operation is invalid or division by zero
        """
        if self._operation is None:
            raise ValueError("No operation selected")
        
        a, b = self._operand_a, self._operand_b
        
        if self._operation == Operation.ADD:
            return add(a, b)
        elif self._operation == Operation.SUBTRACT:
            return subtract(a, b)
        elif self._operation == Operation.MULTIPLY:
            return multiply(a, b)
        elif self._operation == Operation.DIVIDE:
            return divide(a, b)
        elif self._operation == Operation.MODULO:
            if b == 0:
                raise ValueError("Cannot compute modulo with zero")
            return a % b
        elif self._operation == Operation.POWER:
            return a ** b
        
        raise ValueError(f"Unknown operation: {self._operation}")

    def _build_expression(self, result: float) -> str:
        """Build a string representation of the calculation."""
        symbols = {
            Operation.ADD: "+",
            Operation.SUBTRACT: "-",
            Operation.MULTIPLY: "×",
            Operation.DIVIDE: "÷",
            Operation.MODULO: "%",
            Operation.POWER: "^"
        }
        symbol = symbols.get(self._operation, "?")
        return f"{self._operand_a} {symbol} {self._operand_b} = {result}"

    def get_display_result(self) -> str:
        """
        Get formatted result for display.
        
        Returns:
            Formatted string with result or error message
        """
        if not self._history:
            return "No calculations yet"
        
        last_result = self._history[-1]
        if last_result.success:
            return f"Result: {last_result.result}"
        else:
            return f"Error: {last_result.error_message}"

    def get_error_messages(self) -> List[str]:
        """
        Get list of error messages from validation.
        
        Returns:
            List of error message strings
        """
        return [
            msg.message 
            for msg in self._validation_messages 
            if not msg.is_valid
        ]


# Core calculation functions (existing functionality)
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide a by b.
    
    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
