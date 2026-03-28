"""Input validators for analytics API."""

from typing import Any, List, Optional, Tuple

from backend.errors import (
    AnalyticsValidationError,
    ValidationError,
    MalformedDataError,
)

VALID_PERIODS = ("daily", "weekly", "monthly")
VALID_CHART_TYPES = (
    "messages_per_day",
    "users_per_day",
    "conversations_per_day",
    "messages_by_hour",
    "message_type_distribution",
)


def validate_period(period: Optional[str]) -> Tuple[bool, Optional[ValidationError]]:
    """Validate period parameter."""
    if period is None:
        return True, None
    if period not in VALID_PERIODS:
        return False, ValidationError(
            field="period",
            message=f"period must be one of: {', '.join(VALID_PERIODS)}",
            code="INVALID_PERIOD"
        )
    return True, None


def validate_days(days: Optional[int]) -> Tuple[bool, Optional[ValidationError]]:
    """Validate days parameter."""
    if days is None:
        return True, None
    if not isinstance(days, int):
        return False, ValidationError(
            field="days",
            message="days must be an integer",
            code="INVALID_TYPE"
        )
    if days < 1 or days > 365:
        return False, ValidationError(
            field="days",
            message="days must be between 1 and 365",
            code="OUT_OF_RANGE"
        )
    return True, None


def validate_limit(limit: Optional[int]) -> Tuple[bool, Optional[ValidationError]]:
    """Validate limit parameter."""
    if limit is None:
        return True, None
    if not isinstance(limit, int):
        return False, ValidationError(
            field="limit",
            message="limit must be an integer",
            code="INVALID_TYPE"
        )
    if limit < 1 or limit > 100:
        return False, ValidationError(
            field="limit",
            message="limit must be between 1 and 100",
            code="OUT_OF_RANGE"
        )
    return True, None


def validate_chart_type(chart_type: str) -> Tuple[bool, Optional[ValidationError]]:
    """Validate chart_type parameter."""
    if chart_type not in VALID_CHART_TYPES:
        return False, ValidationError(
            field="chart_type",
            message=f"Unknown chart type: {chart_type}. Valid types: {', '.join(VALID_CHART_TYPES)}",
            code="INVALID_CHART_TYPE"
        )
    return True, None


def sanitize_string(value: Any, field_name: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if value is None:
        raise MalformedDataError(
            f"Expected string for {field_name}",
            expected_type="string"
        )
    if not isinstance(value, str):
        raise MalformedDataError(
            f"Expected string for {field_name}",
            expected_type="string"
        )
    sanitized = value[:max_length].strip()
    if not sanitized:
        raise MalformedDataError(
            f"{field_name} cannot be empty",
            expected_type="non-empty string"
        )
    return sanitized


def validate_positive_number(value: Any, field_name: str) -> float:
    """Validate positive number input."""
    try:
        num = float(value)
        if num < 0:
            raise MalformedDataError(
                f"{field_name} cannot be negative",
                expected_type="non-negative number"
            )
        return num
    except (TypeError, ValueError):
        raise MalformedDataError(
            f"Expected numeric value for {field_name}",
            expected_type="number"
        )


def validate_required_fields(data: dict, required: List[str]) -> List[ValidationError]:
    """Validate required fields exist in data."""
    errors = []
    for field in required:
        if field not in data or data[field] is None:
            errors.append(ValidationError(
                field=field,
                message=f"Missing required field: {field}",
                code="MISSING_FIELD"
            ))
    return errors


def normalize_value(value: Any, default: Any = None) -> Any:
    """Normalize a value, returning default if None."""
    if value is None:
        return default
    return value


def get_valid_periods() -> Tuple[str, ...]:
    """Get list of valid period values."""
    return VALID_PERIODS


def get_valid_chart_types() -> Tuple[str, ...]:
    """Get list of valid chart types."""
    return VALID_CHART_TYPES
