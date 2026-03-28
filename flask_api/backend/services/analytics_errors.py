"""Error handling and standardized error responses for analytics API."""

import logging
import traceback
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from datetime import datetime
from flask import jsonify, Request, Response

from backend.errors import (
    AnalyticsValidationError,
    AnalyticsError,
    DataSourceError,
    MalformedDataError,
    ValidationError,
    ErrorResponse as BaseErrorResponse,
    ERROR_CODES,
)

logger = logging.getLogger(__name__)


class ErrorResponse(BaseErrorResponse):
    """Standardized error response with consistent format."""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
        field_errors: Optional[List[Dict[str, str]]] = None,
        request_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        super().__init__(message, code, status_code, details, field_errors)
        self.request_id = request_id
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        error_obj: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp,
        }
        if self.request_id:
            error_obj["request_id"] = self.request_id
        if self.details:
            error_obj["details"] = self.details
        if self.field_errors:
            error_obj["field_errors"] = self.field_errors
        return {"error": error_obj}

    def to_response(self) -> Response:
        response = jsonify(self.to_dict())
        response.status_code = self.status_code
        response.headers["Content-Type"] = "application/json"
        return response


def create_error_response(
    message: str,
    code: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
    field_errors: Optional[List[Dict[str, str]]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Factory function to create standardized error responses."""
    return ErrorResponse(
        message=message,
        code=code,
        status_code=status_code,
        details=details,
        field_errors=field_errors,
        request_id=request_id,
    )


def validation_error_response(
    message: str = "Validation failed",
    field_errors: Optional[List[Dict[str, str]]] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a validation error response."""
    return create_error_response(
        message=message,
        code=ERROR_CODES["VALIDATION_ERROR"],
        status_code=400,
        details=details,
        field_errors=field_errors,
        request_id=request_id,
    )


def not_found_error_response(
    message: str = "Resource not found",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a not found error response."""
    return create_error_response(
        message=message,
        code=ERROR_CODES["NOT_FOUND"],
        status_code=404,
        details=details,
        request_id=request_id,
    )


def data_source_error_response(
    message: str = "Data source error",
    source: str = "database",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a data source error response."""
    return create_error_response(
        message=message,
        code=ERROR_CODES["DATA_SOURCE_ERROR"],
        status_code=503,
        details={"source": source, **(details or {})},
        request_id=request_id,
    )


def malformed_data_error_response(
    message: str = "Malformed data received",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a malformed data error response."""
    return create_error_response(
        message=message,
        code=ERROR_CODES["MALFORMED_DATA"],
        status_code=422,
        details=details,
        request_id=request_id,
    )


def internal_error_response(
    message: str = "An internal error occurred",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    include_traceback: bool = False,
) -> ErrorResponse:
    """Create an internal error response."""
    error_details = details or {}
    if include_traceback:
        error_details["traceback"] = traceback.format_exc()
    
    return create_error_response(
        message=message,
        code=ERROR_CODES["INTERNAL_ERROR"],
        status_code=500,
        details=error_details if error_details else None,
        request_id=request_id,
    )


def rate_limit_error_response(
    message: str = "Rate limit exceeded",
    retry_after: Optional[int] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a rate limit error response."""
    details = {"retry_after": retry_after} if retry_after else None
    response = create_error_response(
        message=message,
        code="RATE_LIMIT_EXCEEDED",
        status_code=429,
        details=details,
        request_id=request_id,
    )
    if retry_after:
        response.headers["Retry-After"] = str(retry_after)
    return response


def unauthorized_error_response(
    message: str = "Unauthorized access",
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create an unauthorized error response."""
    return create_error_response(
        message=message,
        code="UNAUTHORIZED",
        status_code=401,
        request_id=request_id,
    )


def forbidden_error_response(
    message: str = "Forbidden",
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """Create a forbidden error response."""
    return create_error_response(
        message=message,
        code="FORBIDDEN",
        status_code=403,
        request_id=request_id,
    )


def generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    import uuid
    return str(uuid.uuid4())


def handle_service_errors(
    include_traceback: bool = False,
    log_errors: bool = True,
) -> Callable:
    """Decorator to handle service errors and return proper responses.
    
    Args:
        include_traceback: Whether to include traceback in error response
        log_errors: Whether to log errors before returning response
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_id = generate_request_id()
            
            try:
                return func(*args, **kwargs)
            
            except AnalyticsValidationError as e:
                field_errors = [
                    {"field": err.field, "message": err.message, "code": err.code}
                    for err in e.errors
                ]
                if log_errors:
                    logger.warning(
                        f"Validation error [{request_id}]: {e.errors}"
                    )
                return validation_error_response(
                    "Request validation failed",
                    field_errors=field_errors,
                    request_id=request_id,
                ).to_response()
            
            except DataSourceError as e:
                if log_errors:
                    logger.error(
                        f"Data source error [{request_id}] from {e.source}: {e.message}"
                    )
                return data_source_error_response(
                    f"Failed to fetch data from {e.source}: {e.message}",
                    source=e.source,
                    request_id=request_id,
                ).to_response()
            
            except MalformedDataError as e:
                if log_errors:
                    logger.warning(
                        f"Malformed data [{request_id}]: {e.message}"
                    )
                return malformed_data_error_response(
                    f"Data validation failed: {e.message}",
                    details={"expected_type": e.expected_type} if e.expected_type else None,
                    request_id=request_id,
                ).to_response()
            
            except AnalyticsError as e:
                if log_errors:
                    logger.error(
                        f"Analytics error [{request_id}]: {str(e)}"
                    )
                return create_error_response(
                    message=str(e),
                    code="ANALYTICS_ERROR",
                    status_code=500,
                    request_id=request_id,
                ).to_response()
            
            except Exception as e:
                if log_errors:
                    logger.exception(
                        f"Unexpected error [{request_id}] in {func.__name__}: {e}"
                    )
                return internal_error_response(
                    "An unexpected error occurred",
                    details={"error_type": type(e).__name__} if not include_traceback else None,
                    request_id=request_id,
                    include_traceback=include_traceback,
                ).to_response()
        
        return wrapper
    return decorator


def handle_service_errors_with_fallback(
    fallback_value: Any = None,
    log_errors: bool = True,
) -> Callable:
    """Decorator to handle service errors with fallback to default value.
    
    Args:
        fallback_value: Value to return on error
        log_errors: Whether to log errors before returning fallback
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_id = generate_request_id()
            
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                if log_errors:
                    logger.error(
                        f"Error in {func.__name__} [{request_id}]: {e}. "
                        f"Returning fallback value."
                    )
                return fallback_value
        
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handler for analytics endpoints."""
    
    @staticmethod
    def handle_validation_error(
        errors: List[ValidationError],
        request_id: Optional[str] = None,
    ) -> Response:
        """Handle validation errors."""
        field_errors = [
            {"field": err.field, "message": err.message, "code": err.code}
            for err in errors
        ]
        return validation_error_response(
            "Request validation failed",
            field_errors=field_errors,
            request_id=request_id,
        ).to_response()
    
    @staticmethod
    def handle_data_source_error(
        error: DataSourceError,
        request_id: Optional[str] = None,
    ) -> Response:
        """Handle data source errors."""
        logger.error(f"Data source error from {error.source}: {error.message}")
        return data_source_error_response(
            f"Failed to fetch data from {error.source}: {error.message}",
            source=error.source,
            request_id=request_id,
        ).to_response()
    
    @staticmethod
    def handle_malformed_data_error(
        error: MalformedDataError,
        request_id: Optional[str] = None,
    ) -> Response:
        """Handle malformed data errors."""
        logger.warning(f"Malformed data detected: {error.message}")
        return malformed_data_error_response(
            f"Data validation failed: {error.message}",
            details={"expected_type": error.expected_type} if error.expected_type else None,
            request_id=request_id,
        ).to_response()
    
    @staticmethod
    def handle_generic_error(
        error: Exception,
        request_id: Optional[str] = None,
        include_traceback: bool = False,
    ) -> Response:
        """Handle generic errors."""
        logger.exception(f"Unexpected error in request {request_id}: {error}")
        return internal_error_response(
            "An unexpected error occurred",
            details={"error_type": type(error).__name__},
            request_id=request_id,
            include_traceback=include_traceback,
        ).to_response()


def get_error_code_mapping() -> Dict[str, str]:
    """Get mapping of error codes to HTTP status codes."""
    return {
        ERROR_CODES["VALIDATION_ERROR"]: 400,
        ERROR_CODES["INVALID_PERIOD"]: 400,
        ERROR_CODES["INVALID_CHART_TYPE"]: 400,
        ERROR_CODES["OUT_OF_RANGE"]: 400,
        ERROR_CODES["INVALID_TYPE"]: 400,
        ERROR_CODES["MISSING_FIELD"]: 400,
        ERROR_CODES["DATA_SOURCE_ERROR"]: 503,
        ERROR_CODES["MALFORMED_DATA"]: 422,
        ERROR_CODES["INTERNAL_ERROR"]: 500,
        ERROR_CODES["NOT_FOUND"]: 404,
    }


def is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable."""
    if isinstance(error, DataSourceError):
        return True
    if isinstance(error, (MalformedDataError, AnalyticsValidationError)):
        return False
    return True
