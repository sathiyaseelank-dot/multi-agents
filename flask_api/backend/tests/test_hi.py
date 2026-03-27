import pytest
import sys
import os
from datetime import timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.models import db, User
from app.config import Config
from app.hi import validate_name


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
def second_user_headers(client, app):
    with app.app_context():
        user = User(username="seconduser", email="second@example.com")
        user.set_password("password456")
        db.session.add(user)
        db.session.commit()

        response = client.post(
            "/api/auth/login",
            json={"email": "second@example.com", "password": "password456"},
        )
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


class TestValidateName:
    def test_valid_name(self):
        assert validate_name("John") is None

    def test_valid_name_with_spaces(self):
        assert validate_name("  John  ") is None

    def test_valid_name_single_character(self):
        assert validate_name("A") is None

    def test_valid_name_exactly_100_chars(self):
        assert validate_name("a" * 100) is None

    def test_none_name(self):
        assert validate_name(None) == "Name is required"

    def test_empty_string(self):
        assert validate_name("") == "Name is required"

    def test_whitespace_only(self):
        result = validate_name("   ")
        assert result == "Name cannot be empty"

    def test_integer_type(self):
        assert validate_name(123) == "Name must be a string"

    def test_list_type(self):
        assert validate_name(["John"]) == "Name must be a string"

    def test_dict_type(self):
        assert validate_name({"name": "John"}) == "Name must be a string"

    def test_boolean_type(self):
        assert validate_name(True) == "Name must be a string"

    def test_name_exactly_101_chars(self):
        assert validate_name("a" * 101) == "Name must be 100 characters or less"

    def test_name_200_chars(self):
        assert validate_name("a" * 200) == "Name must be 100 characters or less"

    def test_unicode_name(self):
        assert validate_name("José") is None

    def test_cjk_name(self):
        assert validate_name("太郎") is None

    def test_emoji_name(self):
        assert validate_name("👋") is None

    def test_name_with_newline(self):
        assert validate_name("John\nDoe") is None

    def test_name_with_tab(self):
        assert validate_name("John\tDoe") is None


class TestHiPostEndpoint:
    def test_unauthorized(self, client):
        response = client.post("/api/hi", json={"name": "John"})
        assert response.status_code == 401

    def test_success(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": "John"}, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Hi, John!"
        assert "user_id" in data
        assert data["user_id"] is not None

    def test_response_structure(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": "John"}, headers=auth_headers)
        data = response.get_json()
        assert "message" in data
        assert "user_id" in data
        assert "name" not in data or data.get("name") == "John"

    def test_whitespace_trimming(self, client, auth_headers):
        response = client.post(
            "/api/hi", json={"name": "  John  "}, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "Hi, John!" in data["message"]

    def test_missing_name(self, client, auth_headers):
        response = client.post("/api/hi", json={}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Name is required" in data["error"]

    def test_empty_name(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": ""}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_whitespace_only_name(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": "   "}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "Name cannot be empty" in data["error"]

    def test_name_too_long(self, client, auth_headers):
        response = client.post(
            "/api/hi", json={"name": "a" * 101}, headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "100 characters or less" in data["error"]

    def test_name_exactly_100_chars(self, client, auth_headers):
        response = client.post(
            "/api/hi", json={"name": "a" * 100}, headers=auth_headers
        )
        assert response.status_code == 201

    def test_invalid_type_integer(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": 123}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "string" in data["error"]

    def test_invalid_type_list(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": ["John"]}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "string" in data["error"]

    def test_no_json_body(self, client, auth_headers):
        response = client.post(
            "/api/hi", data="{}", content_type="application/json", headers=auth_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_unicode_name(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": "José"}, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert "José" in data["message"]

    def test_cjk_name(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": "太郎"}, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert "太郎" in data["message"]

    def test_single_character_name(self, client, auth_headers):
        response = client.post("/api/hi", json={"name": "A"}, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Hi, A!"

    def test_name_with_special_characters(self, client, auth_headers):
        response = client.post(
            "/api/hi", json={"name": "O'Brien-Smith"}, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "O'Brien-Smith" in data["message"]

    def test_invalid_token(self, client):
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.post("/api/hi", json={"name": "John"}, headers=headers)
        assert response.status_code in (401, 422)

    def test_expired_token(self, client, app):
        from flask_jwt_extended import create_access_token

        with app.app_context():
            user = User(username="expireduser", email="expired@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            uid = str(user.id)

        with app.app_context():
            token = create_access_token(
                identity=uid, expires_delta=timedelta(seconds=-1)
            )

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/hi", json={"name": "John"}, headers=headers)
        assert response.status_code == 401

    def test_user_id_matches_authenticated_user(self, client, auth_headers, app):
        with app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            expected_id = str(user.id)

        response = client.post("/api/hi", json={"name": "John"}, headers=auth_headers)
        data = response.get_json()
        assert str(data["user_id"]) == expected_id


class TestHiGetEndpoint:
    def test_unauthorized(self, client):
        response = client.get("/api/hi")
        assert response.status_code == 401

    def test_success(self, client, auth_headers):
        response = client.get("/api/hi", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "Hi, testuser!" in data["message"]
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == "testuser"

    def test_response_structure(self, client, auth_headers):
        response = client.get("/api/hi", headers=auth_headers)
        data = response.get_json()
        assert "message" in data
        assert "user_id" in data
        assert "username" in data
        assert data["user_id"] is not None

    def test_second_user_greeting(self, client, second_user_headers):
        response = client.get("/api/hi", headers=second_user_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "Hi, seconduser!" in data["message"]
        assert data["username"] == "seconduser"

    def test_user_id_matches(self, client, auth_headers, app):
        with app.app_context():
            user = User.query.filter_by(email="test@example.com").first()
            expected_id = str(user.id)

        response = client.get("/api/hi", headers=auth_headers)
        data = response.get_json()
        assert str(data["user_id"]) == expected_id

    def test_invalid_token(self, client):
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/hi", headers=headers)
        assert response.status_code in (401, 422)

    def test_missing_bearer_prefix(self, client, auth_headers):
        token = auth_headers["Authorization"].split(" ")[1]
        headers = {"Authorization": token}
        response = client.get("/api/hi", headers=headers)
        assert response.status_code == 401


class TestHiHealthCheck:
    def test_health_check(self, client):
        response = client.get("/api/hi/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "hi"

    def test_health_check_no_auth_required(self, client):
        response = client.get("/api/hi/health")
        assert response.status_code == 200

    def test_health_check_post_not_allowed(self, client):
        response = client.post("/api/hi/health")
        assert response.status_code == 405


class TestHiEdgeCases:
    def test_post_with_extra_fields(self, client, auth_headers):
        response = client.post(
            "/api/hi",
            json={"name": "John", "extra": "field", "another": 123},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "Hi, John!" in data["message"]

    def test_post_content_type_mismatch(self, client, auth_headers):
        response = client.post(
            "/api/hi",
            data="name=John",
            content_type="application/x-www-form-urlencoded",
            headers=auth_headers,
        )
        assert response.status_code in (400, 415)

    def test_multiple_requests_same_user(self, client, auth_headers):
        for name in ["Alice", "Bob", "Charlie"]:
            response = client.post("/api/hi", json={"name": name}, headers=auth_headers)
            assert response.status_code == 201
            data = response.get_json()
            assert f"Hi, {name}!" in data["message"]

    def test_get_after_post(self, client, auth_headers):
        client.post("/api/hi", json={"name": "Alice"}, headers=auth_headers)
        response = client.get("/api/hi", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "Hi, testuser!" in data["message"]

    def test_null_json_body(self, client, auth_headers):
        response = client.post(
            "/api/hi",
            data="null",
            content_type="application/json",
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
