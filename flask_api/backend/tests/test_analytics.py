import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.models import db, User, Message
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    BCRYPT_LOG_ROUNDS = 4


@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client, app):
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_data(app):
    with app.app_context():
        users = []
        for i in range(5):
            user = User(username=f"user{i}", email=f"user{i}@example.com")
            user.set_password("password123")
            db.session.add(user)
            users.append(user)
        db.session.commit()

        base_time = datetime.utcnow() - timedelta(days=10)
        for i, user in enumerate(users):
            for j in range(i + 1):
                msg = Message(
                    content=f"Message {j} from {user.username}", user_id=user.id
                )
                msg.created_at = base_time + timedelta(days=j)
                db.session.add(msg)
        db.session.commit()

        return {"users": users}


class TestAnalyticsOverview:
    def test_overview_unauthorized(self, client):
        response = client.get("/api/analytics/overview")
        assert response.status_code == 401

    def test_overview_success(self, client, auth_headers, sample_data):
        response = client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "total_users" in data
        assert "total_messages" in data
        assert "daily_active_users" in data
        assert "monthly_active_users" in data


class TestDailyUsers:
    def test_daily_users_unauthorized(self, client):
        response = client.get("/api/analytics/users/daily")
        assert response.status_code == 401

    def test_daily_users_invalid_date(self, client, auth_headers):
        response = client.get(
            "/api/analytics/users/daily?start_date=invalid", headers=auth_headers
        )
        assert response.status_code == 400

    def test_daily_users_invalid_range(self, client, auth_headers):
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        response = client.get(
            f"/api/analytics/users/daily?start_date={start}&end_date={end}",
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_daily_users_success(self, client, auth_headers, sample_data):
        response = client.get("/api/analytics/users/daily", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert isinstance(data["data"], list)


class TestDailyMessages:
    def test_daily_messages_unauthorized(self, client):
        response = client.get("/api/analytics/messages/daily")
        assert response.status_code == 401

    def test_daily_messages_success(self, client, auth_headers, sample_data):
        response = client.get("/api/analytics/messages/daily", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert isinstance(data["data"], list)


class TestActiveUsers:
    def test_active_users_invalid_period(self, client, auth_headers):
        response = client.get(
            "/api/analytics/users/active?period=invalid", headers=auth_headers
        )
        assert response.status_code == 400

    def test_active_users_daily(self, client, auth_headers, sample_data):
        response = client.get(
            "/api/analytics/users/active?period=daily", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "active_users" in data
        assert data["period"] == "daily"

    def test_active_users_weekly(self, client, auth_headers, sample_data):
        response = client.get(
            "/api/analytics/users/active?period=weekly", headers=auth_headers
        )
        assert response.status_code == 200

    def test_active_users_monthly(self, client, auth_headers, sample_data):
        response = client.get(
            "/api/analytics/users/active?period=monthly", headers=auth_headers
        )
        assert response.status_code == 200


class TestEngagement:
    def test_engagement_unauthorized(self, client):
        response = client.get("/api/analytics/engagement")
        assert response.status_code == 401

    def test_engagement_success(self, client, auth_headers, sample_data):
        response = client.get("/api/analytics/engagement", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "top_users" in data
        assert "total_messages" in data
        assert "avg_messages_per_user" in data

    def test_engagement_limit(self, client, auth_headers, sample_data):
        response = client.get("/api/analytics/engagement?limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["top_users"]) <= 2


class TestRetention:
    def test_retention_unauthorized(self, client):
        response = client.get("/api/analytics/retention")
        assert response.status_code == 401

    def test_retention_success(self, client, auth_headers, sample_data):
        response = client.get("/api/analytics/retention", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "cohort_period_days" in data
        assert "total_users" in data
        assert "retention_rate" in data

    def test_retention_custom_period(self, client, auth_headers, sample_data):
        response = client.get(
            "/api/analytics/retention?cohort_days=7", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["cohort_period_days"] == 7


class TestAnalyticsEdgeCases:
    def test_empty_database(self, client, auth_headers, app):
        with app.app_context():
            Message.query.delete()
            User.query.filter(User.username != "testuser").delete()
            db.session.commit()

        response = client.get("/api/analytics/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_users"] >= 1
        assert data["total_messages"] == 0

    def test_large_limit(self, client, auth_headers):
        response = client.get(
            "/api/analytics/users/daily?limit=500", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]) <= 365


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
