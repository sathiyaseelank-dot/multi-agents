from typing import Any, Dict, List, Optional
from datetime import datetime
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


class ErrorResponse:
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
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        error_obj: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp,
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


def handle_service_errors(func):
    from functools import wraps
    from services.analytics_validation import (
        AnalyticsValidationError,
        DataSourceError,
        MalformedDataError,
    )

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AnalyticsValidationError as e:
            field_errors = [
                {"field": err.field, "message": err.message, "code": err.code}
                for err in e.errors
            ]
            return validation_error_response(
                "Request validation failed", field_errors=field_errors
            ).to_response()
        except DataSourceError as e:
            return data_source_error_response(
                f"Failed to fetch data from {e.source}: {e.message}",
                source=e.source,
            ).to_response()
        except MalformedDataError as e:
            return malformed_data_error_response(
                f"Data validation failed: {e.message}",
                details={"expected_type": e.expected_type} if e.expected_type else None,
            ).to_response()
        except Exception as e:
            return internal_error_response(
                "An unexpected error occurred",
                details={"error_type": type(e).__name__} if not isinstance(e, Exception) else None,
            ).to_response()

    return wrapper
