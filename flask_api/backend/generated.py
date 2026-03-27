from flask import Blueprint, jsonify, request
from functools import wraps
from typing import Any
from services.analytics import AnalyticsService

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


class ValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class DataShapeError(Exception):
    def __init__(self, message: str, expected: str | None = None, received: str | None = None):
        self.message = message
        self.expected = expected
        self.received = received
        super().__init__(message)


class IntegrationError(Exception):
    def __init__(self, message: str, source: str | None = None):
        self.message = message
        self.source = source
        super().__init__(message)


def validate_request(*required_args, **optional_args):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    return decorator


def validate_required_fields(data: dict, required: list) -> None:
    missing = [field for field in required if field not in data or data[field] is None]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}", field=", ".join(missing))


def validate_data_shape(data: Any, expected_type: type, field_name: str = "data") -> None:
    if data is None:
        raise DataShapeError(f"{field_name} is null", expected=str(expected_type), received="null")
    if not isinstance(data, expected_type):
        raise DataShapeError(
            f"{field_name} has invalid type",
            expected=expected_type.__name__,
            received=type(data).__name__
        )


def validate_metric_response(metric: Any, metric_name: str) -> None:
    validate_data_shape(metric, object, metric_name)
    required_fields = ["value", "timestamp", "unit"]
    validate_required_fields(metric.__dict__ if hasattr(metric, "__dict__") else {}, required_fields)


def validate_chart_data(data: dict) -> None:
    validate_data_shape(data, dict, "chart_data")
    if "error" not in data:
        if "labels" not in data and "data" not in data:
            raise DataShapeError(
                "Chart data missing required fields",
                expected="labels and data arrays",
                received=f"keys: {list(data.keys())}"
            )
        if "labels" in data and not isinstance(data["labels"], list):
            raise DataShapeError(
                "Chart labels must be an array",
                expected="list",
                received=type(data["labels"]).__name__
            )
        if "data" in data and not isinstance(data["data"], list):
            raise DataShapeError(
                "Chart data must be an array",
                expected="list",
                received=type(data["data"]).__name__
            )


def validate_list_data(data: Any, field_name: str = "list_data") -> None:
    validate_data_shape(data, list, field_name)
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise DataShapeError(
                f"{field_name}[{idx}] has invalid type",
                expected="dict",
                received=type(item).__name__
            )


def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            return jsonify({
                "error": "validation_error",
                "message": e.message,
                "field": e.field
            }), 400
        except DataShapeError as e:
            return jsonify({
                "error": "data_shape_error",
                "message": e.message,
                "expected": e.expected,
                "received": e.received
            }), 422
        except IntegrationError as e:
            return jsonify({
                "error": "integration_error",
                "message": e.message,
                "source": e.source
            }), 502
        except Exception as e:
            return jsonify({
                "error": "internal_error",
                "message": str(e)
            }), 500
    return wrapper


@bp.route("/overview", methods=["GET"])
@handle_errors
def get_overview():
    data = AnalyticsService.get_dashboard_overview()
    if data is None:
        raise DataShapeError("Dashboard overview returned no data", expected="dict", received="null")
    validate_data_shape(data, dict, "overview")
    return jsonify(data)


@bp.route("/metrics/users", methods=["GET"])
@handle_errors
def get_total_users():
    metric = AnalyticsService.get_total_users()
    if metric is None:
        raise IntegrationError("Failed to retrieve user metrics", source="analytics_service")
    validate_metric_response(metric, "total_users")
    return jsonify(metric.to_dict())


@bp.route("/metrics/messages", methods=["GET"])
@handle_errors
def get_total_messages():
    metric = AnalyticsService.get_total_messages()
    if metric is None:
        raise IntegrationError("Failed to retrieve message metrics", source="analytics_service")
    validate_metric_response(metric, "total_messages")
    return jsonify(metric.to_dict())


@bp.route("/metrics/conversations", methods=["GET"])
@handle_errors
def get_total_conversations():
    metric = AnalyticsService.get_total_conversations()
    if metric is None:
        raise IntegrationError("Failed to retrieve conversation metrics", source="analytics_service")
    validate_metric_response(metric, "total_conversations")
    return jsonify(metric.to_dict())


@bp.route("/metrics/active-users", methods=["GET"])
@handle_errors
def get_active_users():
    period = request.args.get("period", "daily")
    valid_periods = ["daily", "weekly", "monthly"]
    if period not in valid_periods:
        raise ValidationError(
            f"Invalid period '{period}'. Must be one of: {', '.join(valid_periods)}",
            field="period"
        )
    metric = AnalyticsService.get_active_users_count(period=period)
    if metric is None:
        raise IntegrationError(
            f"Failed to retrieve active users for period '{period}'",
            source="analytics_service"
        )
    validate_metric_response(metric, "active_users")
    return jsonify(metric.to_dict())


@bp.route("/charts/<chart_type>", methods=["GET"])
@handle_errors
def get_chart(chart_type):
    valid_chart_types = ["messages", "users", "conversations", "engagement", "retention"]
    if chart_type not in valid_chart_types:
        raise ValidationError(
            f"Invalid chart type '{chart_type}'. Must be one of: {', '.join(valid_chart_types)}",
            field="chart_type"
        )
    
    days = request.args.get("days", 7, type=int)
    if not isinstance(days, int):
        raise ValidationError("days must be an integer", field="days")
    if days < 1 or days > 365:
        raise ValidationError("days must be between 1 and 365", field="days")
    
    data = AnalyticsService.get_chart_data(chart_type, days=days)
    if data is None:
        raise IntegrationError(
            f"Failed to retrieve chart data for type '{chart_type}'",
            source="analytics_service"
        )
    if isinstance(data, dict) and "error" in data:
        raise ValidationError(data["error"], field="chart_data")
    validate_chart_data(data)
    
    if not data.get("labels") or not data.get("data"):
        return jsonify({
            "warning": "Partial dataset returned",
            "labels": data.get("labels", []),
            "data": data.get("data", [])
        }), 206
    
    return jsonify(data)


@bp.route("/top-users", methods=["GET"])
@handle_errors
def get_top_users():
    limit = request.args.get("limit", 10, type=int)
    if not isinstance(limit, int):
        raise ValidationError("limit must be an integer", field="limit")
    if limit < 1 or limit > 100:
        raise ValidationError("limit must be between 1 and 100", field="limit")
    
    data = AnalyticsService.get_top_active_users(limit=limit)
    if data is None:
        raise IntegrationError("Failed to retrieve top users", source="analytics_service")
    validate_list_data(data, "top_users")
    
    if not data:
        return jsonify({
            "warning": "No user data available",
            "users": []
        }), 204
    
    return jsonify({"users": data, "count": len(data)})


@bp.route("/top-conversations", methods=["GET"])
@handle_errors
def get_top_conversations():
    limit = request.args.get("limit", 10, type=int)
    if not isinstance(limit, int):
        raise ValidationError("limit must be an integer", field="limit")
    if limit < 1 or limit > 100:
        raise ValidationError("limit must be between 1 and 100", field="limit")
    
    data = AnalyticsService.get_top_conversations(limit=limit)
    if data is None:
        raise IntegrationError("Failed to retrieve top conversations", source="analytics_service")
    validate_list_data(data, "top_conversations")
    
    if not data:
        return jsonify({
            "warning": "No conversation data available",
            "conversations": []
        }), 204
    
    return jsonify({"conversations": data, "count": len(data)})


@bp.route("/health", methods=["GET"])
def health_check():
    try:
        data = AnalyticsService.get_dashboard_overview()
        if data is not None:
            return jsonify({"status": "healthy", "service": "analytics"}), 200
        return jsonify({"status": "degraded", "service": "analytics"}), 503
    except Exception:
        return jsonify({"status": "unhealthy", "service": "analytics"}), 503
