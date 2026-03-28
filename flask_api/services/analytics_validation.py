from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationError:
    field: str
    message: str
    code: str


class AnalyticsValidationError(Exception):
    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        super().__init__(str(errors))


class DataSourceError(Exception):
    def __init__(self, message: str, source: str = "database"):
        self.message = message
        self.source = source
        super().__init__(message)


class MalformedDataError(Exception):
    def __init__(self, message: str, expected_type: Optional[str] = None):
        self.message = message
        self.expected_type = expected_type
        super().__init__(message)


def validate_period(period: Optional[str]) -> Tuple[bool, Optional[ValidationError]]:
    valid_periods = ("daily", "weekly", "monthly")
    if period is None:
        return True, None
    if period not in valid_periods:
        return False, ValidationError(
            field="period",
            message=f"period must be one of: {', '.join(valid_periods)}",
            code="INVALID_PERIOD"
        )
    return True, None


def validate_days(days: Optional[int]) -> Tuple[bool, Optional[ValidationError]]:
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
    valid_types = (
        "messages_per_day",
        "users_per_day",
        "conversations_per_day",
        "messages_by_hour",
        "message_type_distribution",
    )
    if chart_type not in valid_types:
        return False, ValidationError(
            field="chart_type",
            message=f"Unknown chart type: {chart_type}. Valid types: {', '.join(valid_types)}",
            code="INVALID_CHART_TYPE"
        )
    return True, None


def sanitize_string(value: Any, field_name: str, max_length: int = 255) -> str:
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


def validate_required_fields(data: Dict, required: List[str]) -> List[ValidationError]:
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
    if value is None:
        return default
    return value
