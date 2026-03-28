"""Error handling for analytics backend."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from flask import jsonify


ERROR_CODES = {
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "INVALID_PERIOD": "INVALID_PERIOD",
    "INVALID_CHART_TYPE": "INVALID_CHART_TYPE",
    "OUT_OF_RANGE": "OUT_OF_RANGE",
    "INVALID_TYPE": "INVALID_TYPE",
    "MISSING_FIELD": "MISSING_FIELD",
    "DATA_SOURCE_ERROR": "DATA_SOURCE_ERROR",
    "MALFORMED_DATA": "MALFORMED_DATA",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
    "NOT_FOUND": "NOT_FOUND",
}


@dataclass
class ValidationError:
    """Represents a single validation error."""
    field: str
    message: str
    code: str


class AnalyticsError(Exception):
    """Base exception for analytics errors."""
    pass


class AnalyticsValidationError(AnalyticsError):
    """Exception for validation errors."""
    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        super().__init__(str([e.message for e in errors]))


class DataSourceError(AnalyticsError):
    """Exception for data source errors."""
    def __init__(self, message: str, source: str = "database"):
        self.message = message
        self.source = source
        super().__init__(message)


class MalformedDataError(AnalyticsError):
    """Exception for malformed data errors."""
    def __init__(self, message: str, expected_type: Optional[str] = None):
        self.message = message
        self.expected_type = expected_type
        super().__init__(message)


class ErrorResponse:
    """Standardized error response."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        field_errors: Optional[List[Dict[str, str]]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.field_errors = field_errors or []

    def to_dict(self) -> Dict[str, Any]:
        error_obj: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            error_obj["details"] = self.details
        if self.field_errors:
            error_obj["field_errors"] = self.field_errors
        return {"error": error_obj}

    def to_response(self):
        return jsonify(self.to_dict()), self.status_code


def validation_error_response(
    message: str = "Validation failed",
    field_errors: Optional[List[Dict[str, str]]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
    return ErrorResponse(
        message=message,
        code=ERROR_CODES["VALIDATION_ERROR"],
        status_code=400,
        details=details,
        field_errors=field_errors,
    )


def not_found_error_response(message: str = "Resource not found") -> ErrorResponse:
    return ErrorResponse(
        message=message,
        code=ERROR_CODES["NOT_FOUND"],
        status_code=404,
    )


def data_source_error_response(
    message: str = "Data source error",
    source: str = "database",
    details: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
    return ErrorResponse(
        message=message,
        code=ERROR_CODES["DATA_SOURCE_ERROR"],
        status_code=503,
        details={"source": source, **(details or {})},
    )


def malformed_data_error_response(
    message: str = "Malformed data received",
    details: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
    return ErrorResponse(
        message=message,
        code=ERROR_CODES["MALFORMED_DATA"],
        status_code=422,
        details=details,
    )


def internal_error_response(
    message: str = "An internal error occurred",
    details: Optional[Dict[str, Any]] = None,
) -> ErrorResponse:
    return ErrorResponse(
        message=message,
        code=ERROR_CODES["INTERNAL_ERROR"],
        status_code=500,
        details=details,
    )
