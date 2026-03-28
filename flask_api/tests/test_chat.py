import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch

sys.modules["flask_socketio"] = MagicMock()
sys.modules["eventlet"] = MagicMock()
sys.modules["gevent"] = MagicMock()
sys.modules["geventwebsocket"] = MagicMock()
sys.modules["orchestrator"] = MagicMock()
sys.modules["orchestrator.orchestrator"] = MagicMock()
sys.modules["orchestrator.events"] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from config import TestingConfig
import database
from models import User, Conversation, Message


class TestConversationEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        })
        login_resp = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        self.token = login_resp.get_json()["access_token"]
        
        self.client.post("/api/auth/register", json={
            "username": "seconduser",
            "email": "second@example.com",
            "password": "password123"
        })

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM conversation_participants")
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_get_conversations_empty(self):
        response = self.client.get("/api/chat/conversations", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_get_conversations_unauthorized(self):
        response = self.client.get("/api/chat/conversations")
        self.assertEqual(response.status_code, 401)

    def test_create_direct_conversation(self):
        with self.app.app_context():
            second = User.get_by_username("seconduser")
            second_id = second.id
        
        response = self.client.post("/api/chat/conversations", 
            headers=self._auth_headers(),
            json={"participant_ids": [second_id], "is_group": False}
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["is_group"], False)
        self.assertEqual(len(data["participants"]), 2)

    def test_create_group_conversation(self):
        with self.app.app_context():
            second = User.get_by_username("seconduser")
            second_id = second.id
        
        response = self.client.post("/api/chat/conversations",
            headers=self._auth_headers(),
            json={"participant_ids": [second_id], "is_group": True, "name": "Test Group"}
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["is_group"], True)
        self.assertEqual(data["name"], "Test Group")

    def test_create_conversation_missing_name(self):
        response = self.client.post("/api/chat/conversations",
            headers=self._auth_headers(),
            json={"participant_ids": [], "is_group": True}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.get_json()["error"].lower())

    def test_get_conversation(self):
        with self.app.app_context():
            second = User.get_by_username("seconduser")
            second_id = second.id
        
        conv_response = self.client.post("/api/chat/conversations",
            headers=self._auth_headers(),
            json={"participant_ids": [second_id], "is_group": False}
        )
        conv_id = conv_response.get_json()["id"]
        
        response = self.client.get(f"/api/chat/conversations/{conv_id}", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["id"], conv_id)

    def test_get_conversation_not_participant(self):
        with self.app.app_context():
            other_user = User.create("otheruser", "other@example.com", "hash")
            conversation = Conversation.create(name="Private", is_group=False)
            conversation.add_participant(other_user.id, other_user.id)
            conv_id = conversation.id
        
        response = self.client.get(f"/api/chat/conversations/{conv_id}", headers=self._auth_headers())
        self.assertEqual(response.status_code, 403)


class TestMessageEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        })
        login_resp = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        self.token = login_resp.get_json()["access_token"]
        
        self.client.post("/api/auth/register", json={
            "username": "seconduser",
            "email": "second@example.com",
            "password": "password123"
        })
        
        with self.app.app_context():
            second = User.get_by_username("seconduser")
            second_id = second.id
        
        conv_response = self.client.post("/api/chat/conversations",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"participant_ids": [second_id], "is_group": False}
        )
        self.conv_id = conv_response.get_json()["id"]

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM conversation_participants")
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_send_message(self):
        response = self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
            headers=self._auth_headers(),
            json={"content": "Hello, World!"}
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["content"], "Hello, World!")
        self.assertEqual(data["message_type"], "text")

    def test_send_message_too_long(self):
        response = self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
            headers=self._auth_headers(),
            json={"content": "x" * 10001}
        )
        self.assertEqual(response.status_code, 400)

    def test_get_messages(self):
        for i in range(3):
            self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
                headers=self._auth_headers(),
                json={"content": f"Message {i}"}
            )
        
        response = self.client.get(f"/api/chat/conversations/{self.conv_id}/messages", 
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 3)

    def test_get_messages_pagination(self):
        for i in range(5):
            self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
                headers=self._auth_headers(),
                json={"content": f"Message {i}"}
            )
        
        response = self.client.get(f"/api/chat/conversations/{self.conv_id}/messages?limit=2", 
            headers=self._auth_headers())
        data = response.get_json()
        self.assertEqual(len(data), 2)

    def test_update_message(self):
        msg_response = self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
            headers=self._auth_headers(),
            json={"content": "Original"}
        )
        msg_id = msg_response.get_json()["id"]
        
        response = self.client.put(f"/api/chat/messages/{msg_id}",
            headers=self._auth_headers(),
            json={"content": "Updated"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["content"], "Updated")

    def test_delete_message(self):
        msg_response = self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
            headers=self._auth_headers(),
            json={"content": "To delete"}
        )
        msg_id = msg_response.get_json()["id"]
        
        response = self.client.delete(f"/api/chat/messages/{msg_id}", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)

    def test_mark_message_read(self):
        msg_response = self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
            headers=self._auth_headers(),
            json={"content": "Read me"}
        )
        msg_id = msg_response.get_json()["id"]
        
        response = self.client.post(f"/api/chat/messages/{msg_id}/read", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["is_read"], True)

    def test_mark_conversation_read(self):
        second_login = self.client.post("/api/auth/login", json={
            "username": "seconduser",
            "password": "password123"
        })
        second_token = second_login.get_json()["access_token"]
        
        for _ in range(3):
            self.client.post(f"/api/chat/conversations/{self.conv_id}/messages",
                headers={"Authorization": f"Bearer {second_token}"},
                json={"content": "Mark read"}
            )
        
        response = self.client.post(f"/api/chat/conversations/{self.conv_id}/read", 
            headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["marked_read"], 3)


class TestSearchEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        })
        login_resp = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        self.token = login_resp.get_json()["access_token"]

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM conversation_participants")
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_search_users(self):
        response = self.client.get("/api/chat/users/search?q=test", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_search_users_too_short(self):
        response = self.client.get("/api/chat/users/search?q=a", headers=self._auth_headers())
        self.assertEqual(response.status_code, 400)


class TestParticipantManagement(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        })
        login_resp = self.client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        self.token = login_resp.get_json()["access_token"]
        
        self.client.post("/api/auth/register", json={
            "username": "seconduser",
            "email": "second@example.com",
            "password": "password123"
        })
        
        self.client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123"
        })

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM conversation_participants")
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_add_participant_to_group(self):
        conv_response = self.client.post("/api/chat/conversations",
            headers=self._auth_headers(),
            json={"is_group": True, "name": "Group Chat"}
        )
        conv_id = conv_response.get_json()["id"]
        
        with self.app.app_context():
            new_user = User.get_by_username("newuser")
        
        response = self.client.post(f"/api/chat/conversations/{conv_id}/participants",
            headers=self._auth_headers(),
            json={"user_id": new_user.id}
        )
        self.assertEqual(response.status_code, 200)

    def test_remove_participant_from_group(self):
        with self.app.app_context():
            second = User.get_by_username("seconduser")
            second_id = second.id
        
        conv_response = self.client.post("/api/chat/conversations",
            headers=self._auth_headers(),
            json={"is_group": True, "name": "Group Chat", "participant_ids": [second_id]}
        )
        conv_id = conv_response.get_json()["id"]
        
        response = self.client.delete(
            f"/api/chat/conversations/{conv_id}/participants/{second_id}",
            headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 200)

    def test_cannot_add_to_direct_conversation(self):
        with self.app.app_context():
            second = User.get_by_username("seconduser")
            second_id = second.id
        
        conv_response = self.client.post("/api/chat/conversations",
            headers=self._auth_headers(),
            json={"participant_ids": [second_id], "is_group": False}
        )
        conv_id = conv_response.get_json()["id"]
        
        with self.app.app_context():
            new_user = User.get_by_username("newuser")
        
        response = self.client.post(f"/api/chat/conversations/{conv_id}/participants",
            headers=self._auth_headers(),
            json={"user_id": new_user.id}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
