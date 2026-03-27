from flask import Blueprint, jsonify, request

from services.analytics import AnalyticsService

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.route("/overview", methods=["GET"])
def get_overview():
    try:
        data = AnalyticsService.get_dashboard_overview()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/metrics/users", methods=["GET"])
def get_total_users():
    try:
        metric = AnalyticsService.get_total_users()
        return jsonify(metric.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/metrics/messages", methods=["GET"])
def get_total_messages():
    try:
        metric = AnalyticsService.get_total_messages()
        return jsonify(metric.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/metrics/conversations", methods=["GET"])
def get_total_conversations():
    try:
        metric = AnalyticsService.get_total_conversations()
        return jsonify(metric.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/metrics/active-users", methods=["GET"])
def get_active_users():
    try:
        period = request.args.get("period", "daily")
        if period not in ("daily", "weekly", "monthly"):
            return jsonify({"error": "period must be one of: daily, weekly, monthly"}), 400
        metric = AnalyticsService.get_active_users_count(period=period)
        return jsonify(metric.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/charts/<chart_type>", methods=["GET"])
def get_chart(chart_type):
    try:
        days = request.args.get("days", 7, type=int)
        if days < 1 or days > 365:
            return jsonify({"error": "days must be between 1 and 365"}), 400
        data = AnalyticsService.get_chart_data(chart_type, days=days)
        if "error" in data:
            return jsonify(data), 400
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/top-users", methods=["GET"])
def get_top_users():
    try:
        limit = request.args.get("limit", 10, type=int)
        if limit < 1 or limit > 100:
            return jsonify({"error": "limit must be between 1 and 100"}), 400
        data = AnalyticsService.get_top_active_users(limit=limit)
        return jsonify({"users": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/top-conversations", methods=["GET"])
def get_top_conversations():
    try:
        limit = request.args.get("limit", 10, type=int)
        if limit < 1 or limit > 100:
            return jsonify({"error": "limit must be between 1 and 100"}), 400
        data = AnalyticsService.get_top_conversations(limit=limit)
        return jsonify({"conversations": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/engagement", methods=["GET"])
def get_engagement():
    try:
        data = AnalyticsService.get_engagement_metrics()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/all", methods=["GET"])
def get_all_analytics():
    try:
        data = AnalyticsService.get_all_analytics()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
