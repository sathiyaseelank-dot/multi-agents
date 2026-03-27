import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import create_app
from config import TestingConfig
import database


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    app.config["TESTING"] = True

    with app.app_context():
        database.init_db()

    yield app

    with app.app_context():
        db = database.get_db()
        db.execute("DELETE FROM messages")
        db.execute("DELETE FROM users")
        db.commit()
        db.close()

    db_path = app.config["DATABASE"]
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/users",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/users/login", json={"username": "testuser", "password": "password123"}
    )
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
