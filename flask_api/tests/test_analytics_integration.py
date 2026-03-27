import pytest
import sys
import os
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app import create_app
from app.models import db, User, Message
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    BCRYPT_LOG_ROUNDS = 4


@pytest.fixture
def app():
    application = create_app(TestConfig)
    application.config["TESTING"] = True
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_token(client, app):
    with app.app_context():
        user = User(username="analyst", email="analyst@test.com")
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "analyst@test.com", "password": "pass123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    return resp.get_json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def seeded_data(app):
    """Insert users and messages across multiple days for time-series tests."""
    with app.app_context():
        users = []
        for i in range(10):
            u = User(username=f"seeded{i}", email=f"seeded{i}@test.com")
            u.set_password("pass123")
            db.session.add(u)
            users.append(u)
        db.session.commit()

        now = datetime.utcnow()
        for day_offset in range(30):
            msg_day = now - timedelta(days=day_offset)
            for j in range(day_offset % 5 + 1):
                user_idx = j % len(users)
                msg = Message(
                    content=f"Day-{day_offset}-msg-{j}",
                    user_id=users[user_idx].id,
                )
                msg.created_at = msg_day
                db.session.add(msg)
        db.session.commit()

        return {"users": [u.to_dict() for u in users]}


class TestRequirementsFileIntegrity:
    """Ensure backend requirements.txt is not empty and lists essential packages."""

    def test_requirements_not_empty(self):
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "requirements.txt"
        )
        req_path = os.path.normpath(req_path)
        assert os.path.exists(req_path), f"requirements.txt missing at {req_path}"
        with open(req_path) as f:
            content = f.read().strip()
        assert len(content) > 0, "requirements.txt is empty"

    def test_requirements_has_flask(self):
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "requirements.txt"
        )
        req_path = os.path.normpath(req_path)
        with open(req_path) as f:
            lines = [l.strip().lower() for l in f if l.strip()]
        pkg_names = [l.split("==")[0].split(">=")[0].split("<=")[0] for l in lines]
        assert any("flask" == p for p in pkg_names), (
            "Flask not listed in requirements.txt"
        )

    def test_requirements_has_sqlalchemy(self):
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "requirements.txt"
        )
        req_path = os.path.normpath(req_path)
        with open(req_path) as f:
            lines = [l.strip().lower() for l in f if l.strip()]
        pkg_names = [l.split("==")[0].split(">=")[0].split("<=")[0] for l in lines]
        assert any("sqlalchemy" in p for p in pkg_names), (
            "SQLAlchemy not listed in requirements.txt"
        )

    def test_requirements_has_jwt(self):
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "requirements.txt"
        )
        req_path = os.path.normpath(req_path)
        with open(req_path) as f:
            lines = [l.strip().lower() for l in f if l.strip()]
        pkg_names = [l.split("==")[0].split(">=")[0].split("<=")[0] for l in lines]
        assert any("jwt" in p for p in pkg_names), (
            "Flask-JWT-Extended not listed in requirements.txt"
        )


class TestOverviewChartReadyMetrics:
    """Validate that /overview returns normalized, chart-ready metric values."""

    def test_overview_returns_all_required_keys(
        self, client, auth_headers, seeded_data
    ):
        resp = client.get("/api/analytics/overview", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        required = [
            "total_users",
            "total_messages",
            "daily_active_users",
            "monthly_active_users",
            "new_users_week",
            "messages_today",
            "recent_messages",
        ]
        for key in required:
            assert key in data, f"Missing key: {key}"

    def test_overview_numeric_fields_are_ints(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/overview", headers=auth_headers)
        data = resp.get_json()
        for field in [
            "total_users",
            "total_messages",
            "daily_active_users",
            "monthly_active_users",
            "new_users_week",
            "messages_today",
        ]:
            assert isinstance(data[field], int), (
                f"{field} should be int, got {type(data[field])}"
            )

    def test_overview_recent_messages_have_chart_fields(
        self, client, auth_headers, seeded_data
    ):
        resp = client.get("/api/analytics/overview", headers=auth_headers)
        data = resp.get_json()
        assert isinstance(data["recent_messages"], list)
        for msg in data["recent_messages"]:
            assert "content" in msg
            assert "user_id" in msg
            assert "created_at" in msg
            assert isinstance(msg["created_at"], str)

    def test_overview_total_users_count(self, client, auth_headers, seeded_data, app):
        with app.app_context():
            expected = User.query.count()
        resp = client.get("/api/analytics/overview", headers=auth_headers)
        assert resp.get_json()["total_users"] == expected

    def test_overview_total_messages_count(
        self, client, auth_headers, seeded_data, app
    ):
        with app.app_context():
            expected = Message.query.count()
        resp = client.get("/api/analytics/overview", headers=auth_headers)
        assert resp.get_json()["total_messages"] == expected

    def test_overview_unauthenticated_returns_401(self, client):
        resp = client.get("/api/analytics/overview")
        assert resp.status_code == 401


class TestDailyUsersChartNormalization:
    """Test /users/daily returns properly normalized chart data."""

    def test_daily_users_date_strings_are_iso_format(
        self, client, auth_headers, seeded_data
    ):
        resp = client.get("/api/analytics/users/daily?limit=7", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        for entry in data["data"]:
            assert "date" in entry
            assert "new_users" in entry
            datetime.strptime(entry["date"], "%Y-%m-%d")

    def test_daily_users_contiguous_dates(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/users/daily?limit=10", headers=auth_headers)
        data = resp.get_json()
        dates = [e["date"] for e in data["data"]]
        parsed = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        for i in range(1, len(parsed)):
            diff = (parsed[i] - parsed[i - 1]).days
            assert diff == 1, f"Gap between {dates[i - 1]} and {dates[i]}"

    def test_daily_users_zero_fill_missing_dates(self, client, auth_headers, app):
        with app.app_context():
            u = User(username="lonely", email="lonely@test.com")
            u.set_password("p")
            db.session.add(u)
            old_date = datetime.utcnow() - timedelta(days=20)
            u.created_at = old_date
            db.session.commit()
        resp = client.get(
            "/api/analytics/users/daily?limit=30",
            headers=auth_headers,
        )
        data = resp.get_json()
        counts = [e["new_users"] for e in data["data"]]
        zeros = [c for c in counts if c == 0]
        assert len(zeros) >= 20, "Expected zero-fill for dates with no registrations"

    def test_daily_users_custom_date_range(self, client, auth_headers, seeded_data):
        start = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        end = datetime.utcnow().strftime("%Y-%m-%d")
        resp = client.get(
            f"/api/analytics/users/daily?start_date={start}&end_date={end}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["start_date"] == start
        assert data["end_date"] == end
        assert len(data["data"]) == 8

    def test_daily_users_invalid_start_date_format(self, client, auth_headers):
        resp = client.get(
            "/api/analytics/users/daily?start_date=not-a-date",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_daily_users_invalid_end_date_format(self, client, auth_headers):
        resp = client.get(
            "/api/analytics/users/daily?end_date=32-13-9999",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_daily_users_start_after_end_rejected(self, client, auth_headers):
        start = datetime.utcnow().strftime("%Y-%m-%d")
        end = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        resp = client.get(
            f"/api/analytics/users/daily?start_date={start}&end_date={end}",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_daily_users_range_exceeds_365_rejected(self, client, auth_headers):
        start = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
        end = datetime.utcnow().strftime("%Y-%m-%d")
        resp = client.get(
            f"/api/analytics/users/daily?start_date={start}&end_date={end}",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_daily_users_limit_capped(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/users/daily?limit=999", headers=auth_headers)
        data = resp.get_json()
        assert len(data["data"]) <= 365

    def test_daily_users_default_limit_30(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/users/daily", headers=auth_headers)
        data = resp.get_json()
        assert len(data["data"]) == 30

    def test_daily_users_unauthenticated(self, client):
        resp = client.get("/api/analytics/users/daily")
        assert resp.status_code == 401


class TestDailyMessagesChartNormalization:
    """Test /messages/daily returns properly normalized chart data."""

    def test_daily_messages_chart_structure(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/messages/daily?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data
        assert "start_date" in data
        assert "end_date" in data
        for entry in data["data"]:
            assert "date" in entry
            assert "messages" in entry
            assert isinstance(entry["messages"], int)
            datetime.strptime(entry["date"], "%Y-%m-%d")

    def test_daily_messages_contiguous(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/messages/daily?limit=7", headers=auth_headers)
        data = resp.get_json()
        dates = [e["date"] for e in data["data"]]
        parsed = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        for i in range(1, len(parsed)):
            assert (parsed[i] - parsed[i - 1]).days == 1

    def test_daily_messages_zero_fill(self, client, auth_headers, app):
        with app.app_context():
            u = User(username="msguser", email="msg@test.com")
            u.set_password("p")
            db.session.add(u)
            db.session.commit()
            msg = Message(content="one message", user_id=u.id)
            msg.created_at = datetime.utcnow() - timedelta(days=5)
            db.session.add(msg)
            db.session.commit()
        resp = client.get(
            "/api/analytics/messages/daily?limit=10", headers=auth_headers
        )
        data = resp.get_json()
        zeros = [e for e in data["data"] if e["messages"] == 0]
        assert len(zeros) >= 5

    def test_daily_messages_invalid_date(self, client, auth_headers):
        resp = client.get(
            "/api/analytics/messages/daily?start_date=2024/01/01",
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_daily_messages_invalid_range(self, client, auth_headers):
        end = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        start = datetime.utcnow().strftime("%Y-%m-%d")
        resp = client.get(
            f"/api/analytics/messages/daily?start_date={start}&end_date={end}",
            headers=auth_headers,
        )
        # start == end is valid, start > end should fail
        start2 = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        resp2 = client.get(
            f"/api/analytics/messages/daily?start_date={start2}&end_date={end}",
            headers=auth_headers,
        )
        assert resp2.status_code == 400

    def test_daily_messages_unauthenticated(self, client):
        resp = client.get("/api/analytics/messages/daily")
        assert resp.status_code == 401


class TestActiveUsersEndpoint:
    """Validate /users/active for each period and error handling."""

    def test_active_users_daily_chart_response(self, client, auth_headers, seeded_data):
        resp = client.get(
            "/api/analytics/users/active?period=daily", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["period"] == "daily"
        assert isinstance(data["active_users"], int)

    def test_active_users_weekly(self, client, auth_headers, seeded_data):
        resp = client.get(
            "/api/analytics/users/active?period=weekly", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.get_json()["period"] == "weekly"

    def test_active_users_monthly(self, client, auth_headers, seeded_data):
        resp = client.get(
            "/api/analytics/users/active?period=monthly", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.get_json()["period"] == "monthly"

    def test_active_users_invalid_period(self, client, auth_headers):
        resp = client.get(
            "/api/analytics/users/active?period=yearly", headers=auth_headers
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_active_users_empty_period(self, client, auth_headers):
        resp = client.get("/api/analytics/users/active", headers=auth_headers)
        assert resp.status_code == 200

    def test_active_users_unauthenticated(self, client):
        resp = client.get("/api/analytics/users/active?period=daily")
        assert resp.status_code == 401

    def test_active_users_no_data_returns_zero(self, client, auth_headers, app):
        with app.app_context():
            Message.query.delete()
            db.session.commit()
        resp = client.get(
            "/api/analytics/users/active?period=daily", headers=auth_headers
        )
        assert resp.get_json()["active_users"] == 0


class TestEngagementEndpoint:
    """Validate /engagement returns normalized top-user metrics."""

    def test_engagement_returns_chart_ready_list(
        self, client, auth_headers, seeded_data
    ):
        resp = client.get("/api/analytics/engagement", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["top_users"], list)
        for user in data["top_users"]:
            assert "user_id" in user
            assert "username" in user
            assert "message_count" in user
            assert isinstance(user["message_count"], int)

    def test_engagement_sorted_descending(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/engagement?limit=20", headers=auth_headers)
        data = resp.get_json()
        counts = [u["message_count"] for u in data["top_users"]]
        assert counts == sorted(counts, reverse=True)

    def test_engagement_limit_respected(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/engagement?limit=3", headers=auth_headers)
        data = resp.get_json()
        assert len(data["top_users"]) <= 3

    def test_engagement_limit_max_100(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/engagement?limit=999", headers=auth_headers)
        data = resp.get_json()
        assert len(data["top_users"]) <= 100

    def test_engagement_avg_messages_is_float(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/engagement", headers=auth_headers)
        data = resp.get_json()
        assert isinstance(data["avg_messages_per_user"], (int, float))

    def test_engagement_unauthenticated(self, client):
        resp = client.get("/api/analytics/engagement")
        assert resp.status_code == 401

    def test_engagement_empty_data(self, client, auth_headers, app):
        with app.app_context():
            Message.query.delete()
            db.session.commit()
        resp = client.get("/api/analytics/engagement", headers=auth_headers)
        data = resp.get_json()
        assert data["top_users"] == []
        assert data["total_messages"] == 0
        assert data["avg_messages_per_user"] == 0


class TestRetentionEndpoint:
    """Validate /retention rate calculation and chart-ready output."""

    def test_retention_returns_all_keys(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/retention", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        for key in [
            "cohort_period_days",
            "total_users",
            "returning_users",
            "retention_rate",
        ]:
            assert key in data, f"Missing key: {key}"

    def test_retention_rate_is_percentage(self, client, auth_headers, seeded_data):
        resp = client.get("/api/analytics/retention", headers=auth_headers)
        data = resp.get_json()
        assert 0 <= data["retention_rate"] <= 100

    def test_retention_custom_cohort(self, client, auth_headers, seeded_data):
        resp = client.get(
            "/api/analytics/retention?cohort_days=14", headers=auth_headers
        )
        data = resp.get_json()
        assert data["cohort_period_days"] == 14

    def test_retention_cohort_capped_90(self, client, auth_headers, seeded_data):
        resp = client.get(
            "/api/analytics/retention?cohort_days=200", headers=auth_headers
        )
        data = resp.get_json()
        assert data["cohort_period_days"] == 90

    def test_retention_unauthenticated(self, client):
        resp = client.get("/api/analytics/retention")
        assert resp.status_code == 401

    def test_retention_no_new_users_returns_zero(self, client, auth_headers, app):
        with app.app_context():
            Message.query.delete()
            # Push all remaining users outside the cohort window
            for u in User.query.all():
                u.created_at = datetime.utcnow() - timedelta(days=200)
            db.session.commit()
        resp = client.get(
            "/api/analytics/retention?cohort_days=30", headers=auth_headers
        )
        data = resp.get_json()
        assert data["total_users"] == 0
        assert data["retention_rate"] == 0


class TestHelperFunctions:
    """Unit tests for analytics helper functions."""

    def test_validate_date_range_valid(self):
        from app.analytics import validate_date_range

        start = datetime.utcnow() - timedelta(days=30)
        end = datetime.utcnow()
        valid, error = validate_date_range(start, end)
        assert valid is True
        assert error is None

    def test_validate_date_range_start_after_end(self):
        from app.analytics import validate_date_range

        start = datetime.utcnow()
        end = datetime.utcnow() - timedelta(days=1)
        valid, error = validate_date_range(start, end)
        assert valid is False
        assert "before" in error.lower()

    def test_validate_date_range_exceeds_365(self):
        from app.analytics import validate_date_range

        start = datetime.utcnow() - timedelta(days=400)
        end = datetime.utcnow()
        valid, error = validate_date_range(start, end)
        assert valid is False
        assert "365" in error

    def test_parse_date_param_none_returns_default(self):
        from app.analytics import parse_date_param

        result = parse_date_param(None, 7)
        expected = datetime.utcnow() - timedelta(days=7)
        assert abs((result - expected).total_seconds()) < 2

    def test_parse_date_param_valid_string(self):
        from app.analytics import parse_date_param

        result = parse_date_param("2025-06-15")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15

    def test_parse_date_param_invalid_string(self):
        from app.analytics import parse_date_param

        result = parse_date_param("invalid-date")
        assert result is None

    def test_format_date_none(self):
        from app.analytics import format_date

        assert format_date(None) is None

    def test_format_date_datetime(self):
        from app.analytics import format_date

        dt = datetime(2025, 3, 15, 10, 30)
        assert format_date(dt) == "2025-03-15"

    def test_format_date_string_passthrough(self):
        from app.analytics import format_date

        assert format_date("already-string") == "already-string"


class TestHealthEndpoint:
    """Verify the health check endpoint works with analytics blueprint registered."""

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "healthy"


class TestCrossEndpointDataConsistency:
    """Ensure data consistency across multiple analytics endpoints."""

    def test_overview_and_daily_users_agree(self, client, auth_headers, seeded_data):
        overview = client.get(
            "/api/analytics/overview", headers=auth_headers
        ).get_json()
        daily = client.get(
            "/api/analytics/users/daily?limit=7", headers=auth_headers
        ).get_json()
        total_from_daily = sum(e["new_users"] for e in daily["data"])
        # daily covers only last 7 days; overview covers all time
        assert total_from_daily <= overview["total_users"]

    def test_overview_and_engagement_message_counts(
        self, client, auth_headers, seeded_data
    ):
        overview = client.get(
            "/api/analytics/overview", headers=auth_headers
        ).get_json()
        engagement = client.get(
            "/api/analytics/engagement", headers=auth_headers
        ).get_json()
        assert overview["total_messages"] == engagement["total_messages"]
