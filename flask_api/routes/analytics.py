from flask import Blueprint, jsonify, request

from services.analytics import AnalyticsService
from services.analytics_validation import (
    validate_period,
    validate_days,
    validate_limit,
    validate_chart_type,
    AnalyticsValidationError,
    ValidationError,
    DataSourceError,
    MalformedDataError,
)
from services.analytics_errors import (
    ErrorResponse,
    validation_error_response,
    not_found_error_response,
    data_source_error_response,
    malformed_data_error_response,
    internal_error_response,
    handle_service_errors,
)

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.errorhandler(AnalyticsValidationError)
def handle_validation_error(error):
    field_errors = [
        {"field": err.field, "message": err.message, "code": err.code}
        for err in error.errors
    ]
    return validation_error_response(
        "Request validation failed", field_errors=field_errors
    ).to_response()


@bp.errorhandler(DataSourceError)
def handle_data_source_error(error):
    return data_source_error_response(
        f"Failed to fetch data from {error.source}: {error.message}",
        source=error.source,
    ).to_response()


@bp.errorhandler(MalformedDataError)
def handle_malformed_data_error(error):
    return malformed_data_error_response(
        f"Data validation failed: {error.message}",
        details={"expected_type": error.expected_type} if error.expected_type else None,
    ).to_response()


def validate_request(*validators):
    def decorator(func):
        def wrapper(*args, **kwargs):
            errors = []
            for validator in validators:
                valid, error = validator()
                if not valid and error:
                    errors.append(error)
            if errors:
                raise AnalyticsValidationError(errors)
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def get_period_param():
    period = request.args.get("period")
    if period:
        return validate_period(period)
    return True, None


def get_days_param(default=7):
    days = request.args.get("days", default, type=int)
    return validate_days(days)


def get_limit_param(default=10):
    limit = request.args.get("limit", default, type=int)
    return validate_limit(limit)


@bp.route("/overview", methods=["GET"])
@handle_service_errors
def get_overview():
    data = AnalyticsService.get_dashboard_overview()
    return jsonify(data)


@bp.route("/metrics/users", methods=["GET"])
@handle_service_errors
def get_total_users():
    metric = AnalyticsService.get_total_users()
    return jsonify(metric.to_dict())


@bp.route("/metrics/messages", methods=["GET"])
@handle_service_errors
def get_total_messages():
    metric = AnalyticsService.get_total_messages()
    return jsonify(metric.to_dict())


@bp.route("/metrics/conversations", methods=["GET"])
@handle_service_errors
def get_total_conversations():
    metric = AnalyticsService.get_total_conversations()
    return jsonify(metric.to_dict())


@bp.route("/metrics/active-users", methods=["GET"])
@handle_service_errors
def get_active_users():
    period = request.args.get("period", "daily")
    valid, error = validate_period(period)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    metric = AnalyticsService.get_active_users_count(period=period)
    return jsonify(metric.to_dict())


@bp.route("/charts/<chart_type>", methods=["GET"])
@handle_service_errors
def get_chart(chart_type):
    valid, error = validate_chart_type(chart_type)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    days = request.args.get("days", 7, type=int)
    valid, error = validate_days(days)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    data = AnalyticsService.get_chart_data(chart_type, days=days)
    if "error" in data:
        return validation_error_response(
            data["error"],
            field_errors=[{"field": "chart_type", "message": data["error"], "code": "CHART_ERROR"}]
        ).to_response()
    
    return jsonify(data)


@bp.route("/top-users", methods=["GET"])
@handle_service_errors
def get_top_users():
    limit = request.args.get("limit", 10, type=int)
    valid, error = validate_limit(limit)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    data = AnalyticsService.get_top_active_users(limit=limit)
    return jsonify({"users": data})


@bp.route("/top-conversations", methods=["GET"])
@handle_service_errors
def get_top_conversations():
    limit = request.args.get("limit", 10, type=int)
    valid, error = validate_limit(limit)
    if not valid and error:
        raise AnalyticsValidationError([error])
    
    data = AnalyticsService.get_top_conversations(limit=limit)
    return jsonify({"conversations": data})


@bp.route("/engagement", methods=["GET"])
@handle_service_errors
def get_engagement():
    data = AnalyticsService.get_engagement_metrics()
    return jsonify(data)


@bp.route("/all", methods=["GET"])
@handle_service_errors
def get_all_analytics():
    data = AnalyticsService.get_all_analytics()
    return jsonify(data)
