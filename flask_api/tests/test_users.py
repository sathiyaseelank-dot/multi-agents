import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from config import TestingConfig
import database


class UserAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            database.init_db()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM users")
            db.commit()
            db.close()

        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_create_user_success(self):
        response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@example.com")
        self.assertIn("id", data)
        self.assertIn("created_at", data)

    def test_create_user_missing_fields(self):
        response = self.client.post("/api/users", json={"username": "testuser"})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_create_user_duplicate_username(self):
        self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test1@example.com",
                "password": "password123",
            },
        )
        response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test2@example.com",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertIn("error", data)

    def test_create_user_duplicate_email(self):
        self.client.post(
            "/api/users",
            json={
                "username": "user1",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        response = self.client.post(
            "/api/users",
            json={
                "username": "user2",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertIn("error", data)

    def test_create_user_empty_json(self):
        response = self.client.post("/api/users", json={})
        self.assertEqual(response.status_code, 400)

    def test_get_all_users_empty(self):
        response = self.client.get("/api/users")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data, [])

    def test_get_all_users(self):
        self.client.post(
            "/api/users",
            json={
                "username": "user1",
                "email": "user1@example.com",
                "password": "password123",
            },
        )
        self.client.post(
            "/api/users",
            json={
                "username": "user2",
                "email": "user2@example.com",
                "password": "password123",
            },
        )

        response = self.client.get("/api/users")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_get_user_by_id_success(self):
        create_response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        user_id = create_response.get_json()["id"]

        response = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], "testuser")

    def test_get_user_by_id_not_found(self):
        response = self.client.get("/api/users/99999")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("error", data)

    def test_update_user_success(self):
        create_response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        user_id = create_response.get_json()["id"]

        response = self.client.put(
            f"/api/users/{user_id}", json={"username": "updateduser"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], "updateduser")

    def test_update_user_with_password(self):
        create_response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        user_id = create_response.get_json()["id"]

        response = self.client.put(
            f"/api/users/{user_id}", json={"password": "newpassword"}
        )
        self.assertEqual(response.status_code, 200)

    def test_update_user_not_found(self):
        response = self.client.put("/api/users/99999", json={"username": "updated"})
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("error", data)

    def test_update_user_empty_json(self):
        create_response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        user_id = create_response.get_json()["id"]

        response = self.client.put(f"/api/users/{user_id}", json={})
        self.assertEqual(response.status_code, 400)

    def test_delete_user_success(self):
        create_response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        user_id = create_response.get_json()["id"]

        response = self.client.delete(f"/api/users/{user_id}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("message", data)

        get_response = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(get_response.status_code, 404)

    def test_delete_user_not_found(self):
        response = self.client.delete("/api/users/99999")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
