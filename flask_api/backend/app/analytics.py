from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Message
from datetime import datetime, timedelta
from sqlalchemy import func, and_

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


def validate_date_range(start_date, end_date):
    if start_date > end_date:
        return False, "start_date must be before end_date"
    if (end_date - start_date).days > 365:
        return False, "Date range cannot exceed 365 days"
    return True, None


def parse_date_param(date_str, default_days_ago=30):
    if not date_str:
        return datetime.utcnow() - timedelta(days=default_days_ago)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def format_date(dt):
    if dt is None:
        return None
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


@analytics_bp.route("/overview", methods=["GET"])
@jwt_required()
def get_overview():
    try:
        total_users = User.query.count()
        total_messages = Message.query.count()

        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())

        dau = User.query.filter(User.created_at >= today_start).count()
        dau = max(
            dau,
            Message.query.filter(Message.created_at >= today_start)
            .distinct(Message.user_id)
            .count(),
        )

        thirty_days_ago = today_start - timedelta(days=30)
        mau = (
            db.session.query(func.count(func.distinct(Message.user_id)))
            .filter(Message.created_at >= thirty_days_ago)
            .scalar()
            or 0
        )

        week_ago = today_start - timedelta(days=7)
        new_users_week = User.query.filter(User.created_at >= week_ago).count()

        messages_today = Message.query.filter(Message.created_at >= today_start).count()

        recent_messages = (
            Message.query.order_by(Message.created_at.desc()).limit(5).all()
        )

        return jsonify(
            {
                "total_users": total_users,
                "total_messages": total_messages,
                "daily_active_users": dau,
                "monthly_active_users": mau,
                "new_users_week": new_users_week,
                "messages_today": messages_today,
                "recent_messages": [msg.to_dict() for msg in recent_messages],
            }
        ), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch overview: {str(e)}"}), 500


@analytics_bp.route("/users/daily", methods=["GET"])
@jwt_required()
def get_daily_users():
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    limit = request.args.get("limit", 30, type=int)

    limit = min(limit, 365)

    end_date = parse_date_param(end_date_str, 0)
    start_date = parse_date_param(start_date_str, limit)

    if not end_date or not start_date:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    valid, error = validate_date_range(start_date, end_date)
    if not valid:
        return jsonify({"error": error}), 400

    users_by_date = (
        db.session.query(
            func.date(User.created_at).label("date"), func.count(User.id).label("count")
        )
        .filter(
            and_(
                func.date(User.created_at) >= start_date.date(),
                func.date(User.created_at) <= end_date.date(),
            )
        )
        .group_by(func.date(User.created_at))
        .all()
    )

    date_map = {format_date(row.date): row.count for row in users_by_date}

    result = []
    current = start_date
    while current <= end_date:
        date_str = format_date(current)
        result.append({"date": date_str, "new_users": date_map.get(date_str, 0)})
        current += timedelta(days=1)

    return jsonify(
        {
            "start_date": format_date(start_date),
            "end_date": format_date(end_date),
            "data": result,
        }
    ), 200


@analytics_bp.route("/messages/daily", methods=["GET"])
@jwt_required()
def get_daily_messages():
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    limit = request.args.get("limit", 30, type=int)

    limit = min(limit, 365)

    end_date = parse_date_param(end_date_str, 0)
    start_date = parse_date_param(start_date_str, limit)

    if not end_date or not start_date:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    valid, error = validate_date_range(start_date, end_date)
    if not valid:
        return jsonify({"error": error}), 400

    messages_by_date = (
        db.session.query(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .filter(
            and_(
                func.date(Message.created_at) >= start_date.date(),
                func.date(Message.created_at) <= end_date.date(),
            )
        )
        .group_by(func.date(Message.created_at))
        .all()
    )

    date_map = {format_date(row.date): row.count for row in messages_by_date}

    result = []
    current = start_date
    while current <= end_date:
        date_str = format_date(current)
        result.append({"date": date_str, "messages": date_map.get(date_str, 0)})
        current += timedelta(days=1)

    return jsonify(
        {
            "start_date": format_date(start_date),
            "end_date": format_date(end_date),
            "data": result,
        }
    ), 200


@analytics_bp.route("/users/active", methods=["GET"])
@jwt_required()
def get_active_users():
    period = request.args.get("period", "daily")

    if period not in ["daily", "weekly", "monthly"]:
        return jsonify(
            {"error": "Invalid period. Use 'daily', 'weekly', or 'monthly'"}
        ), 400

    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    if period == "daily":
        active_users = (
            Message.query.filter(Message.created_at >= today_start)
            .distinct(Message.user_id)
            .count()
        )
    elif period == "weekly":
        week_ago = today_start - timedelta(days=7)
        active_users = (
            Message.query.filter(Message.created_at >= week_ago)
            .distinct(Message.user_id)
            .count()
        )
    else:
        month_ago = today_start - timedelta(days=30)
        active_users = (
            Message.query.filter(Message.created_at >= month_ago)
            .distinct(Message.user_id)
            .count()
        )

    return jsonify({"period": period, "active_users": active_users}), 200


@analytics_bp.route("/engagement", methods=["GET"])
@jwt_required()
def get_engagement_metrics():
    limit = request.args.get("limit", 10, type=int)
    limit = min(limit, 100)

    top_users = (
        db.session.query(
            User.id, User.username, func.count(Message.id).label("message_count")
        )
        .join(Message, User.id == Message.user_id)
        .group_by(User.id, User.username)
        .order_by(func.count(Message.id).desc())
        .limit(limit)
        .all()
    )

    total_messages = Message.query.count()

    user_message_counts = (
        db.session.query(func.count(Message.id))
        .join(User)
        .group_by(Message.user_id)
        .all()
    )

    avg_messages_per_user = 0
    if user_message_counts:
        avg_messages_per_user = sum([row[0] for row in user_message_counts]) / len(
            user_message_counts
        )

    return jsonify(
        {
            "top_users": [
                {
                    "user_id": row.id,
                    "username": row.username,
                    "message_count": row.message_count,
                }
                for row in top_users
            ],
            "total_messages": total_messages,
            "avg_messages_per_user": round(avg_messages_per_user, 2),
        }
    ), 200


@analytics_bp.route("/retention", methods=["GET"])
@jwt_required()
def get_retention():
    cohort_days = request.args.get("cohort_days", 30, type=int)
    cohort_days = min(cohort_days, 90)

    today = datetime.utcnow().date()
    cohort_start = today - timedelta(days=cohort_days)

    new_users = User.query.filter(
        and_(
            func.date(User.created_at) >= cohort_start,
            func.date(User.created_at) <= today,
        )
    ).all()

    returning = 0
    for user in new_users:
        has_activity_after_day_one = (
            Message.query.filter(
                and_(
                    Message.user_id == user.id,
                    Message.created_at > user.created_at + timedelta(days=1),
                )
            ).first()
            is not None
        )
        if has_activity_after_day_one:
            returning += 1

    retention_rate = (returning / len(new_users) * 100) if new_users else 0

    return jsonify(
        {
            "cohort_period_days": cohort_days,
            "total_users": len(new_users),
            "returning_users": returning,
            "retention_rate": round(retention_rate, 2),
        }
    ), 200
