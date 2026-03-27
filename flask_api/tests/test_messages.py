import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from config import TestingConfig
import database


class MessageAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            database.init_db()
            self._create_test_users()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()

        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_test_users(self):
        response = self.client.post(
            "/api/users",
            json={
                "username": "user1",
                "email": "user1@example.com",
                "password": "pass1",
            },
        )
        self.user1_id = response.get_json()["id"]

        response = self.client.post(
            "/api/users",
            json={
                "username": "user2",
                "email": "user2@example.com",
                "password": "pass2",
            },
        )
        self.user2_id = response.get_json()["id"]

    def _login(self, username, password):
        response = self.client.post(
            "/api/users/login", json={"username": username, "password": password}
        )
        return response.get_json()["access_token"]

    def test_send_message_success(self):
        token = self._login("user1", "pass1")
        response = self.client.post(
            "/api/messages",
            json={"receiver_id": self.user2_id, "content": "Hello!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["content"], "Hello!")
        self.assertEqual(data["sender_id"], self.user1_id)
        self.assertEqual(data["receiver_id"], self.user2_id)

    def test_send_message_unauthorized(self):
        response = self.client.post(
            "/api/messages",
            json={"receiver_id": self.user2_id, "content": "Hello!"},
        )
        self.assertEqual(response.status_code, 401)

    def test_send_message_missing_content(self):
        token = self._login("user1", "pass1")
        response = self.client.post(
            "/api/messages",
            json={"receiver_id": self.user2_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_send_message_to_nonexistent_user(self):
        token = self._login("user1", "pass1")
        response = self.client.post(
            "/api/messages",
            json={"receiver_id": 99999, "content": "Hello!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 404)

    def test_get_conversation(self):
        token = self._login("user1", "pass1")
        self.client.post(
            "/api/messages",
            json={"receiver_id": self.user2_id, "content": "Hello!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.client.post(
            "/api/messages",
            json={"receiver_id": self.user1_id, "content": "Hi back!"},
            headers={"Authorization": f"Bearer {self._login('user2', 'pass2')}"},
        )

        response = self.client.get(
            f"/api/messages/conversation/{self.user2_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_get_conversations(self):
        token = self._login("user1", "pass1")
        self.client.post(
            "/api/messages",
            json={"receiver_id": self.user2_id, "content": "Hello!"},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = self.client.get(
            "/api/messages/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["user"]["id"], self.user2_id)


if __name__ == "__main__":
    unittest.main()
