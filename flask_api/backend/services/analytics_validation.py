"""Input validators for analytics API with comprehensive validation."""

import logging
from typing import Any, List, Optional, Tuple

from backend.errors import (
    AnalyticsValidationError,
    ValidationError,
    MalformedDataError,
    DataSourceError,
)

logger = logging.getLogger(__name__)

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


def validate_request_params(params: dict, schema: dict) -> Tuple[bool, List[ValidationError]]:
    """Validate request parameters against a schema.
    
    Args:
        params: Dictionary of request parameters
        schema: Dictionary defining expected params and their validators
        
    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []
    
    for field, rules in schema.items():
        value = params.get(field)
        
        if rules.get("required", False) and value is None:
            errors.append(ValidationError(
                field=field,
                message=f"Missing required parameter: {field}",
                code="MISSING_FIELD"
            ))
            continue
        
        if value is not None:
            if "type" in rules:
                expected_type = rules["type"]
                if expected_type == "int" and not isinstance(value, int):
                    try:
                        value = int(value)
                        params[field] = value
                    except (ValueError, TypeError):
                        errors.append(ValidationError(
                            field=field,
                            message=f"{field} must be an integer",
                            code="INVALID_TYPE"
                        ))
                        continue
            
            if "min" in rules and value < rules["min"]:
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} must be at least {rules['min']}",
                    code="OUT_OF_RANGE"
                ))
            
            if "max" in rules and value > rules["max"]:
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} must be at most {rules['max']}",
                    code="OUT_OF_RANGE"
                ))
            
            if "allowed" in rules and value not in rules["allowed"]:
                errors.append(ValidationError(
                    field=field,
                    message=f"{field} must be one of: {', '.join(map(str, rules['allowed']))}",
                    code="INVALID_VALUE"
                ))
    
    return len(errors) == 0, errors


def validate_response_schema(data: Any, expected_type: str) -> Tuple[bool, Optional[str]]:
    """Validate response data matches expected schema.
    
    Args:
        data: Response data to validate
        expected_type: Expected type name (e.g., 'DashboardMetric', 'ChartData')
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if data is None:
        return False, f"{expected_type} response is null"
    
    if expected_type == "DashboardMetric":
        required = ["id", "label", "value"]
        for field in required:
            if field not in data:
                return False, f"DashboardMetric missing required field: {field}"
    
    elif expected_type == "ChartData":
        required = ["chart_type", "data"]
        for field in required:
            if field not in data:
                return False, f"ChartData missing required field: {field}"
        if not isinstance(data.get("data"), list):
            return False, "ChartData 'data' must be an array"
    
    elif expected_type == "DashboardOverview":
        required = ["metrics", "generated_at"]
        for field in required:
            if field not in data:
                return False, f"DashboardOverview missing required field: {field}"
        if not isinstance(data.get("metrics"), list):
            return False, "DashboardOverview 'metrics' must be an array"
    
    elif expected_type == "EngagementMetrics":
        required = ["avg_messages_per_user", "active_users_7d", "engagement_rate", "total_users"]
        for field in required:
            if field not in data:
                return False, f"EngagementMetrics missing required field: {field}"
    
    elif expected_type == "ListData":
        if not isinstance(data, list):
            return False, "Expected list data"
    
    return True, None


def validate_query_params(params: dict) -> Tuple[bool, List[ValidationError]]:
    """Validate and sanitize query parameters.
    
    Args:
        params: Dictionary of query parameters from request
        
    Returns:
        Tuple of (is_valid, list of validation errors)
    """
    errors = []
    
    if "days" in params:
        days = params["days"]
        valid, error = validate_days(days)
        if not valid:
            errors.append(error)
    
    if "limit" in params:
        limit = params["limit"]
        valid, error = validate_limit(limit)
        if not valid:
            errors.append(error)
    
    if "period" in params:
        period = params["period"]
        valid, error = validate_period(period)
        if not valid:
            errors.append(error)
    
    if "chart_type" in params:
        chart_type = params["chart_type"]
        valid, error = validate_chart_type(chart_type)
        if not valid:
            errors.append(error)
    
    return len(errors) == 0, errors


def log_validation_error(error: ValidationError) -> None:
    """Log validation error for debugging."""
    logger.warning(
        f"Validation error: field={error.field}, code={error.code}, message={error.message}"
    )


def log_data_source_error(error: DataSourceError) -> None:
    """Log data source error for debugging."""
    logger.error(
        f"Data source error: source={error.source}, message={error.message}"
    )


def log_malformed_data_error(error: MalformedDataError) -> None:
    """Log malformed data error for debugging."""
    logger.warning(
        f"Malformed data: message={error.message}, expected={error.expected_type}"
    )
