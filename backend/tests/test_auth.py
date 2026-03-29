import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["FLASK_ENV"] = "testing"

from app import create_app
from config import TestingConfig
from database import init_db, get_db
from models import User, Session, LoginAttemptTracker


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()


class TestRegistration:
    def test_register_success(self, client, db):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"

    def test_register_missing_fields(self, client, db):
        response = client.post("/api/auth/register", json={"username": "testuser"})
        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_register_invalid_email(self, client, db):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "email" in data["error"]["details"]

    def test_register_weak_password(self, client, db):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "weak",
            },
        )
        assert response.status_code == 422
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "password" in data["error"]["details"]

    def test_register_duplicate_username(self, client, db, app):
        with app.app_context():
            User.create("testuser", "test1@example.com", "SecurePass123!")

        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test2@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409
        data = response.get_json()
        assert data["error"]["code"] == "REGISTRATION_FAILED"

    def test_register_duplicate_email(self, client, db, app):
        with app.app_context():
            User.create("testuser1", "test@example.com", "SecurePass123!")

        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser2",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 409


class TestLogin:
    def test_login_success(self, client, db, app):
        with app.app_context():
            User.create("testuser", "test@example.com", "SecurePass123!")

        response = client.post(
            "/api/auth/login",
            json={"identifier": "testuser", "password": "SecurePass123!"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "tokens" in data
        assert "access_token" in data["tokens"]

    def test_login_with_email(self, client, db, app):
        with app.app_context():
            User.create("testuser", "test@example.com", "SecurePass123!")

        response = client.post(
            "/api/auth/login",
            json={"identifier": "test@example.com", "password": "SecurePass123!"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_login_invalid_password(self, client, db, app):
        with app.app_context():
            User.create("testuser", "test@example.com", "SecurePass123!")

        response = client.post(
            "/api/auth/login",
            json={"identifier": "testuser", "password": "WrongPassword123!"},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"
        assert "remaining_attempts" in data["error"]["details"]

    def test_login_invalid_username(self, client, db):
        response = client.post(
            "/api/auth/login",
            json={"identifier": "nonexistent", "password": "SomePassword123!"},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "INVALID_CREDENTIALS"

    def test_login_missing_credentials(self, client, db):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422
        data = response.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_login_nonexistent_user(self, client, db):
        response = client.post(
            "/api/auth/login",
            json={"identifier": "ghostuser", "password": "SecurePass123!"},
        )
        assert response.status_code == 401


class TestTokenRefresh:
    def test_refresh_success(self, client, db, app):
        with app.app_context():
            user = User.create("testuser", "test@example.com", "SecurePass123!")
            refresh_token = Session.create(user.id, "refresh")

        response = client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token.token}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_refresh_invalid_token(self, client, db):
        response = client.post(
            "/api/auth/refresh", json={"refresh_token": "invalid-token"}
        )
        assert response.status_code == 401

    def test_refresh_missing_token(self, client, db):
        response = client.post("/api/auth/refresh", json={})
        assert response.status_code == 422


class TestLogout:
    def test_logout_success(self, client, db, app):
        with app.app_context():
            user = User.create("testuser", "test@example.com", "SecurePass123!")
            access_token = Session.create(user.id, "access")

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token.token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_logout_without_token(self, client, db):
        response = client.post("/api/auth/logout")
        assert response.status_code == 401

    def test_logout_all_devices(self, client, db, app):
        with app.app_context():
            user = User.create("testuser", "test@example.com", "SecurePass123!")
            access_token = Session.create(user.id, "access")

        response = client.post(
            "/api/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token.token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestGetCurrentUser:
    def test_get_me_success(self, client, db, app):
        with app.app_context():
            user = User.create("testuser", "test@example.com", "SecurePass123!")
            access_token = Session.create(user.id, "access")

        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access_token.token}"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["username"] == "testuser"

    def test_get_me_without_token(self, client, db):
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestVerifyToken:
    def test_verify_valid_token(self, client, db, app):
        with app.app_context():
            user = User.create("testuser", "test@example.com", "SecurePass123!")
            access_token = Session.create(user.id, "access")

        response = client.post(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {access_token.token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["valid"] is True

    def test_verify_invalid_token(self, client, db):
        response = client.post(
            "/api/auth/verify", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestPasswordHashing:
    def test_password_hashed_with_bcrypt(self, app, db):
        with app.app_context():
            password = "SecurePass123!"
            hashed = User.hash_password(password)

            assert hashed != password
            assert hashed.startswith("$2")
            assert len(hashed) == 60

    def test_password_verification(self, app, db):
        with app.app_context():
            user = User.create("testuser", "test@example.com", "SecurePass123!")

            assert User.verify_password(user, "SecurePass123!")
            assert not User.verify_password(user, "WrongPassword123!")


class TestValidation:
    def test_username_too_short(self, client, db):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422
        data = response.get_json()
        assert "username" in data["error"]["details"]

    def test_username_with_special_chars(self, client, db):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "test@user",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422
        data = response.get_json()
        assert "username" in data["error"]["details"]

    def test_email_invalid_format(self, client, db):
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "notanemail",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code == 422
        data = response.get_json()
        assert "email" in data["error"]["details"]
