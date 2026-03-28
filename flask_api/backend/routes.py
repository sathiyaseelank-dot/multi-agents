"""API routes for analytics backend."""

import logging
from functools import wraps
from flask import Blueprint, jsonify, request, Response
from typing import Any, Dict, List, Optional

from backend.services.analytics import AnalyticsService
from backend.services.analytics_validation import (
    validate_chart_type,
    validate_days,
    validate_limit,
    validate_period,
    validate_response_schema,
    AnalyticsValidationError,
    DataSourceError,
    MalformedDataError,
)
from backend.services.analytics_validation import ValidationError as AnalyticsValidationErrorType
from backend.services.analytics_errors import (
    ErrorResponse,
    validation_error_response,
    data_source_error_response,
    malformed_data_error_response,
    internal_error_response,
    handle_service_errors as base_handle_errors,
    generate_request_id,
)


def validate_chart_data(data: Any, chart_type: str) -> None:
    """Validate chart data response structure."""
    if data is None:
        raise DataSourceError(
            f"Chart data for {chart_type} returned null",
            source="analytics_service"
        )
    if not isinstance(data, dict):
        raise MalformedDataError(
            f"Chart data must be a dictionary",
            expected_type="dict"
        )
    if "error" in data:
        raise AnalyticsValidationError([
            AnalyticsValidationErrorType(
                field="chart_type",
                message=data["error"],
                code="CHART_ERROR"
            )
        ])
    if "data" not in data:
        raise MalformedDataError(
            "Chart data missing required 'data' field",
            expected_type="dict with 'data' key"
        )
    if not isinstance(data.get("data"), list):
        raise MalformedDataError(
            "Chart data field must be an array",
            expected_type="list"
        )


def validate_list_data(data: Any, field_name: str = "list_data") -> None:
    """Validate list data response structure."""
    if data is None:
        raise DataSourceError(
            f"{field_name} returned null",
            source="analytics_service"
        )
    if not isinstance(data, list):
        raise MalformedDataError(
            f"{field_name} must be an array",
            expected_type="list"
        )


def validate_overview_data(data: Any) -> None:
    """Validate dashboard overview response structure."""
    if data is None:
        raise DataSourceError(
            "Dashboard overview returned null",
            source="analytics_service"
        )
    if not isinstance(data, dict):
        raise MalformedDataError(
            "Dashboard overview must be a dictionary",
            expected_type="dict"
        )
    if "metrics" not in data:
        raise MalformedDataError(
            "Dashboard overview missing 'metrics' field",
            expected_type="dict with 'metrics' key"
        )
    if not isinstance(data.get("metrics"), list):
        raise MalformedDataError(
            "Dashboard metrics must be an array",
            expected_type="list"
        )


def validate_metric_response(metric: Any, metric_name: str) -> bool:
    """Validate that a metric response has required fields."""
    if metric is None:
        raise MalformedDataError(
            f"{metric_name} returned null",
            expected_type="DashboardMetric"
        )
    if isinstance(metric, dict):
        required_fields = ["id", "label", "value"]
        for field in required_fields:
            if field not in metric:
                raise MalformedDataError(
                    f"{metric_name} missing required field: {field}",
                    expected_type="DashboardMetric with fields: " + ", ".join(required_fields)
                )
    return True


def validate_response(response_data: Any, expected_type: str) -> bool:
    """Validate response data against expected schema."""
    is_valid, error_msg = validate_response_schema(response_data, expected_type)
    if not is_valid:
        raise MalformedDataError(str(error_msg), expected_type=expected_type)
    return True


def add_response_headers(response: Response, request_id: str) -> Response:
    """Add standard headers to response."""
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def create_success_response(
    data: Any,
    status_code: int = 200,
    request_id: Optional[str] = None,
) -> Response:
    """Create a standardized success response."""
    response = jsonify(data)
    response.status_code = status_code
    if request_id:
        response = add_response_headers(response, request_id)
    return response

logger = logging.getLogger(__name__)

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


def handle_service_errors(func):
    """Decorator to handle service errors and return proper responses."""
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
            logger.error(f"Data source error from {e.source}: {e.message}")
            return data_source_error_response(
                f"Failed to fetch data from {e.source}: {e.message}",
                source=e.source,
            ).to_response()
        except MalformedDataError as e:
            logger.warning(f"Malformed data detected: {e.message}")
            return malformed_data_error_response(
                f"Data validation failed: {e.message}",
                details={"expected_type": e.expected_type} if e.expected_type else None,
            ).to_response()
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            return internal_error_response(
                "An unexpected error occurred",
                details={"error_type": type(e).__name__},
            ).to_response()
    return wrapper


@bp.route("/overview", methods=["GET"])
@handle_service_errors
def get_overview():
    """Get dashboard overview with key metrics."""
    service = AnalyticsService()
    data = service.get_dashboard_overview()
    response_data = data.to_dict()
    validate_response(response_data, "DashboardOverview")
    return create_success_response(response_data, request_id=generate_request_id())


@bp.route("/metrics/users", methods=["GET"])
@handle_service_errors
def get_total_users():
    """Get total users metric."""
    service = AnalyticsService()
    metric = service.get_total_users()
    response_data = metric.to_dict()
    validate_response(response_data, "DashboardMetric")
    return create_success_response(response_data, request_id=generate_request_id())


@bp.route("/metrics/messages", methods=["GET"])
@handle_service_errors
def get_total_messages():
    """Get total messages metric."""
    service = AnalyticsService()
    metric = service.get_total_messages()
    response_data = metric.to_dict()
    validate_response(response_data, "DashboardMetric")
    return create_success_response(response_data, request_id=generate_request_id())


@bp.route("/metrics/conversations", methods=["GET"])
@handle_service_errors
def get_total_conversations():
    """Get total conversations metric."""
    service = AnalyticsService()
    metric = service.get_total_conversations()
    response_data = metric.to_dict()
    validate_response(response_data, "DashboardMetric")
    return create_success_response(response_data, request_id=generate_request_id())


@bp.route("/metrics/active-users", methods=["GET"])
@handle_service_errors
def get_active_users():
    """Get active users metric.
    
    Query params:
        period: daily, weekly, or monthly (default: daily)
    """
    period = request.args.get("period", "daily")
    valid, error = validate_period(period)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    metric = service.get_active_users_count(period=period)
    response_data = metric.to_dict()
    validate_response(response_data, "DashboardMetric")
    return create_success_response(response_data, request_id=generate_request_id())


@bp.route("/charts/<chart_type>", methods=["GET"])
@handle_service_errors
def get_chart(chart_type):
    """Get chart data for a specific chart type.
    
    Path params:
        chart_type: Type of chart (messages_per_day, users_per_day, etc.)
    
    Query params:
        days: Number of days for data (default: 7, max: 365)
    """
    valid, error = validate_chart_type(chart_type)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    days = request.args.get("days", 7, type=int)
    valid, error = validate_days(days)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_chart_data(chart_type, days=days)
    
    if "error" in data:
        return validation_error_response(
            data["error"],
            field_errors=[{"field": "chart_type", "message": data["error"], "code": "CHART_ERROR"}]
        ).to_response()
    
    validate_response(data, "ChartData")
    return create_success_response(data, request_id=generate_request_id())


@bp.route("/charts/messages-per-day", methods=["GET"])
@handle_service_errors
def get_messages_per_day():
    """Get messages per day chart data.
    
    Query params:
        days: Number of days (default: 7)
    """
    days = request.args.get("days", 7, type=int)
    valid, error = validate_days(days)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_messages_per_day(days)
    return jsonify({
        "chart_type": "messages_per_day",
        "data": [dp.to_dict() for dp in data],
    })


@bp.route("/charts/users-per-day", methods=["GET"])
@handle_service_errors
def get_users_per_day():
    """Get users per day chart data.
    
    Query params:
        days: Number of days (default: 7)
    """
    days = request.args.get("days", 7, type=int)
    valid, error = validate_days(days)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_users_per_day(days)
    return jsonify({
        "chart_type": "users_per_day",
        "data": [dp.to_dict() for dp in data],
    })


@bp.route("/charts/conversations-per-day", methods=["GET"])
@handle_service_errors
def get_conversations_per_day():
    """Get conversations per day chart data.
    
    Query params:
        days: Number of days (default: 7)
    """
    days = request.args.get("days", 7, type=int)
    valid, error = validate_days(days)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_conversations_per_day(days)
    return jsonify({
        "chart_type": "conversations_per_day",
        "data": [dp.to_dict() for dp in data],
    })


@bp.route("/charts/messages-by-hour", methods=["GET"])
@handle_service_errors
def get_messages_by_hour():
    """Get messages by hour chart data.
    
    Query params:
        days: Number of days (default: 7)
    """
    days = request.args.get("days", 7, type=int)
    valid, error = validate_days(days)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_messages_by_hour(days)
    return jsonify({
        "chart_type": "messages_by_hour",
        "data": [dp.to_dict() for dp in data],
    })


@bp.route("/charts/message-types", methods=["GET"])
@handle_service_errors
def get_message_types():
    """Get message type distribution chart data."""
    service = AnalyticsService()
    data = service.get_message_type_distribution()
    return jsonify({
        "chart_type": "message_type_distribution",
        "data": [dp.to_dict() for dp in data],
    })


@bp.route("/top-users", methods=["GET"])
@handle_service_errors
def get_top_users():
    """Get top active users.
    
    Query params:
        limit: Maximum number of users (default: 10, max: 100)
    """
    limit = request.args.get("limit", 10, type=int)
    valid, error = validate_limit(limit)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_top_active_users(limit=limit)
    return jsonify({"users": data})


@bp.route("/top-conversations", methods=["GET"])
@handle_service_errors
def get_top_conversations():
    """Get top conversations.
    
    Query params:
        limit: Maximum number of conversations (default: 10, max: 100)
    """
    limit = request.args.get("limit", 10, type=int)
    valid, error = validate_limit(limit)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    service = AnalyticsService()
    data = service.get_top_conversations(limit=limit)
    return jsonify({"conversations": data})


@bp.route("/engagement", methods=["GET"])
@handle_service_errors
def get_engagement():
    """Get engagement metrics."""
    service = AnalyticsService()
    data = service.get_engagement_metrics()
    response_data = data.to_dict()
    validate_response(response_data, "EngagementMetrics")
    return create_success_response(response_data, request_id=generate_request_id())


@bp.route("/all", methods=["GET"])
@handle_service_errors
def get_all_analytics():
    """Get all analytics data for dashboard."""
    service = AnalyticsService()
    data = service.get_all_analytics()
    validate_response(data, "AnalyticsResponse")
    return create_success_response(data, request_id=generate_request_id())


@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    try:
        service = AnalyticsService()
        overview = service.get_dashboard_overview()
        if overview is not None:
            return jsonify({"status": "healthy", "service": "analytics"}), 200
        return jsonify({"status": "degraded", "service": "analytics"}), 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "service": "analytics"}), 503
