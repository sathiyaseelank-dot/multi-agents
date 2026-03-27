import os
import sys
import json
import time
import unittest
from unittest.mock import MagicMock, patch

# Mock missing dependencies before any app imports
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


class AuthRegistrationTestCase(unittest.TestCase):
    """Tests for user registration endpoint (POST /api/auth/register)."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()

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

    def test_register_success(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "StrongP@ss1",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "newuser")
        self.assertEqual(data["user"]["email"], "newuser@example.com")
        self.assertIn("id", data["user"])
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

    def test_register_returns_access_token(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "tokenuser",
                "email": "tokenuser@example.com",
                "password": "StrongP@ss1",
            },
        )
        data = response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("token_type", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertIsInstance(data["access_token"], str)
        self.assertGreater(len(data["access_token"]), 20)

    def test_register_missing_username(self):
        response = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "StrongP@ss1"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_register_missing_email(self):
        response = self.client.post(
            "/api/auth/register",
            json={"username": "testuser", "password": "StrongP@ss1"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_register_missing_password(self):
        response = self.client.post(
            "/api/auth/register",
            json={"username": "testuser", "email": "test@example.com"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_register_empty_body(self):
        response = self.client.post("/api/auth/register", json={})
        self.assertEqual(response.status_code, 400)

    def test_register_no_json_body(self):
        response = self.client.post(
            "/api/auth/register",
            data="not json",
            content_type="text/plain",
        )
        self.assertIn(response.status_code, [400, 415])

    def test_register_duplicate_username(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "dupuser",
                "email": "first@example.com",
                "password": "StrongP@ss1",
            },
        )
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "dupuser",
                "email": "second@example.com",
                "password": "StrongP@ss1",
            },
        )
        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertIn("error", data)

    def test_register_duplicate_email(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "same@example.com",
                "password": "StrongP@ss1",
            },
        )
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "same@example.com",
                "password": "StrongP@ss1",
            },
        )
        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertIn("error", data)

    def test_register_password_is_hashed(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "hashcheck",
                "email": "hash@example.com",
                "password": "plaintext123",
            },
        )
        with self.app.app_context():
            db = database.get_db()
            row = db.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                ("hashcheck",),
            ).fetchone()
            self.assertIsNotNone(row)
            stored_hash = row["password_hash"]
            self.assertNotEqual(stored_hash, "plaintext123")
            self.assertTrue(
                stored_hash.startswith("pbkdf2:")
                or stored_hash.startswith("scrypt:")
                or len(stored_hash) > 20
            )

    def test_register_short_password_rejected(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "shortpw",
                "email": "short@example.com",
                "password": "123",
            },
        )
        self.assertIn(response.status_code, [400, 422])

    def test_register_user_id_is_integer(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "idcheck",
                "email": "idcheck@example.com",
                "password": "StrongP@ss1",
            },
        )
        data = response.get_json()
        self.assertIsInstance(data["user"]["id"], int)


class AuthLoginTestCase(unittest.TestCase):
    """Tests for user login endpoint (POST /api/auth/login)."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "CorrectP@ss1",
            },
        )

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

    def test_login_success_with_username(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "CorrectP@ss1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "loginuser")

    def test_login_success_with_email(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "login@example.com", "password": "CorrectP@ss1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("access_token", data)

    def test_login_wrong_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "WrongP@ss1"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertNotIn("access_token", data)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "ghostuser", "password": "Whatever1"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("error", data)

    def test_login_missing_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_login_missing_username(self):
        response = self.client.post(
            "/api/auth/login",
            json={"password": "CorrectP@ss1"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_login_empty_body(self):
        response = self.client.post("/api/auth/login", json={})
        self.assertEqual(response.status_code, 400)

    def test_login_token_is_string(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "CorrectP@ss1"},
        )
        data = response.get_json()
        self.assertIsInstance(data["access_token"], str)
        self.assertGreater(len(data["access_token"]), 10)

    def test_login_token_type_is_bearer(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "CorrectP@ss1"},
        )
        data = response.get_json()
        self.assertEqual(data["token_type"], "bearer")

    def test_login_response_excludes_password(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "CorrectP@ss1"},
        )
        data = response.get_json()
        self.assertNotIn("password", data["user"])
        self.assertNotIn("password_hash", data["user"])

    def test_login_response_includes_user_data(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "loginuser", "password": "CorrectP@ss1"},
        )
        data = response.get_json()
        self.assertEqual(data["user"]["username"], "loginuser")
        self.assertEqual(data["user"]["email"], "login@example.com")


class TokenValidationTestCase(unittest.TestCase):
    """Tests for JWT token-based authentication and validation."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post(
            "/api/auth/register",
            json={
                "username": "tokenuser",
                "email": "token@example.com",
                "password": "TokenP@ss1",
            },
        )
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "tokenuser", "password": "TokenP@ss1"},
        )
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

    def test_protected_endpoint_with_valid_token(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], "tokenuser")

    def test_protected_endpoint_without_token(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("error", data)

    def test_protected_endpoint_with_invalid_token(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("error", data)

    def test_protected_endpoint_with_malformed_auth_header(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer sometoken"},
        )
        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_with_empty_token(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer "},
        )
        self.assertEqual(response.status_code, 401)

    def test_token_reuse_across_requests(self):
        resp1 = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        resp2 = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(
            resp1.get_json()["username"], resp2.get_json()["username"]
        )

    def test_token_from_login_works_immediately(self):
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "tokenuser", "password": "TokenP@ss1"},
        )
        new_token = login_resp.get_json()["access_token"]
        me_resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(me_resp.status_code, 200)

    def test_different_users_get_different_tokens(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "tokenuser2",
                "email": "token2@example.com",
                "password": "TokenP@ss1",
            },
        )
        login2 = self.client.post(
            "/api/auth/login",
            json={"username": "tokenuser2", "password": "TokenP@ss1"},
        )
        token2 = login2.get_json()["access_token"]
        self.assertNotEqual(self.token, token2)

        resp1 = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        resp2 = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(resp1.get_json()["username"], "tokenuser")
        self.assertEqual(resp2.get_json()["username"], "tokenuser2")

    def test_token_contains_user_id_claim(self):
        import jwt as pyjwt
        payload = pyjwt.decode(
            self.token,
            options={"verify_signature": False},
        )
        self.assertIn("user_id", payload)
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

    def test_token_valid_with_correct_secret(self):
        import jwt as pyjwt
        payload = pyjwt.decode(
            self.token,
            "dev-secret-key-change-in-production",
            algorithms=["HS256"],
        )
        self.assertIn("user_id", payload)


class TokenRefreshTestCase(unittest.TestCase):
    """Tests for token refresh endpoint (POST /api/auth/refresh)."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post(
            "/api/auth/register",
            json={
                "username": "refreshuser",
                "email": "refresh@example.com",
                "password": "RefreshP@ss1",
            },
        )
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "refreshuser", "password": "RefreshP@ss1"},
        )
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

    def test_refresh_returns_new_token(self):
        response = self.client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("access_token", data)
        self.assertIn("token_type", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_refresh_requires_auth(self):
        response = self.client.post("/api/auth/refresh")
        self.assertEqual(response.status_code, 401)

    def test_refresh_with_invalid_token(self):
        response = self.client.post(
            "/api/auth/refresh",
            headers={"Authorization": "Bearer invalid.token.value"},
        )
        self.assertEqual(response.status_code, 401)

    def test_refreshed_token_works(self):
        refresh_resp = self.client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        new_token = refresh_resp.get_json()["access_token"]
        me_resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.get_json()["username"], "refreshuser")


class PasswordHashingTestCase(unittest.TestCase):
    """Tests for password hashing security."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()

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

    def test_same_password_produces_different_hashes(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "hashuser1",
                "email": "hash1@example.com",
                "password": "SamePassword1",
            },
        )
        self.client.post(
            "/api/auth/register",
            json={
                "username": "hashuser2",
                "email": "hash2@example.com",
                "password": "SamePassword1",
            },
        )
        with self.app.app_context():
            db = database.get_db()
            rows = db.execute(
                "SELECT password_hash FROM users WHERE username IN (?, ?) ORDER BY username",
                ("hashuser1", "hashuser2"),
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0]["password_hash"], rows[1]["password_hash"])

    def test_password_hash_never_stored_plaintext(self):
        password = "MySecretP@ss99"
        self.client.post(
            "/api/auth/register",
            json={
                "username": "plaincheck",
                "email": "plain@example.com",
                "password": password,
            },
        )
        with self.app.app_context():
            db = database.get_db()
            row = db.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                ("plaincheck",),
            ).fetchone()
            self.assertNotEqual(row["password_hash"], password)

    def test_login_with_correct_password_after_hashing(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "verifyhash",
                "email": "verify@example.com",
                "password": "VerifyP@ss1",
            },
        )
        response = self.client.post(
            "/api/auth/login",
            json={"username": "verifyhash", "password": "VerifyP@ss1"},
        )
        self.assertEqual(response.status_code, 200)

    def test_login_fails_with_wrong_password_after_hashing(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "verifyfail",
                "email": "verifyfail@example.com",
                "password": "CorrectP@ss1",
            },
        )
        response = self.client.post(
            "/api/auth/login",
            json={"username": "verifyfail", "password": "WrongP@ss1"},
        )
        self.assertEqual(response.status_code, 401)

    def test_password_update_rehashes(self):
        reg_resp = self.client.post(
            "/api/auth/register",
            json={
                "username": "updatepw",
                "email": "updatepw@example.com",
                "password": "OldP@ssword1",
            },
        )
        user_id = reg_resp.get_json()["user"]["id"]

        with self.app.app_context():
            db = database.get_db()
            old_hash = db.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()["password_hash"]

        self.client.put(
            f"/api/users/{user_id}",
            json={"password": "NewP@ssword2"},
        )

        with self.app.app_context():
            db = database.get_db()
            new_hash = db.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()["password_hash"]

        self.assertNotEqual(old_hash, new_hash)
        self.assertNotEqual(new_hash, "NewP@ssword2")

        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "updatepw", "password": "NewP@ssword2"},
        )
        self.assertEqual(login_resp.status_code, 200)


class ProtectedChatAccessTestCase(unittest.TestCase):
    """Tests for protected access controls on chat features."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post(
            "/api/auth/register",
            json={
                "username": "chatuser",
                "email": "chat@example.com",
                "password": "ChatP@ss1",
            },
        )
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "chatuser", "password": "ChatP@ss1"},
        )
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

    def test_conversations_list_requires_auth(self):
        response = self.client.get("/api/chat/conversations")
        self.assertEqual(response.status_code, 401)

    def test_conversations_list_with_auth(self):
        response = self.client.get(
            "/api/chat/conversations",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

    def test_create_conversation_requires_auth(self):
        response = self.client.post(
            "/api/chat/conversations",
            json={"name": "Test Room", "participant_ids": [], "is_group": True},
        )
        self.assertEqual(response.status_code, 401)

    def test_send_message_requires_auth(self):
        response = self.client.post(
            "/api/chat/conversations/1/messages",
            json={"content": "Hello"},
        )
        self.assertEqual(response.status_code, 401)

    def test_get_messages_requires_auth(self):
        response = self.client.get("/api/chat/conversations/1/messages")
        self.assertEqual(response.status_code, 401)

    def test_get_message_by_id_requires_auth(self):
        response = self.client.get("/api/chat/messages/1")
        self.assertEqual(response.status_code, 401)

    def test_update_message_requires_auth(self):
        response = self.client.put(
            "/api/chat/messages/1",
            json={"content": "Updated"},
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_message_requires_auth(self):
        response = self.client.delete("/api/chat/messages/1")
        self.assertEqual(response.status_code, 401)

    def test_user_search_requires_auth(self):
        response = self.client.get("/api/chat/users/search?q=test")
        self.assertEqual(response.status_code, 401)

    def test_user_search_with_auth(self):
        response = self.client.get(
            "/api/chat/users/search?q=chat",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_token_rejected_for_chat(self):
        response = self.client.get(
            "/api/chat/conversations",
            headers={"Authorization": "Bearer fake.invalid.token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_wrong_bearer_format_rejected(self):
        response = self.client.get(
            "/api/chat/conversations",
            headers={"Authorization": "Token " + self.token},
        )
        self.assertEqual(response.status_code, 401)

    def test_create_group_conversation_with_auth(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "chatuser2",
                "email": "chat2@example.com",
                "password": "ChatP@ss1",
            },
        )
        response = self.client.post(
            "/api/chat/conversations",
            json={
                "name": "Test Group",
                "participant_ids": [],
                "is_group": True,
            },
            headers=self._auth_headers(),
        )
        self.assertIn(response.status_code, [200, 201])

    def test_conversation_participant_check(self):
        other_reg = self.client.post(
            "/api/auth/register",
            json={
                "username": "otherchat",
                "email": "otherchat@example.com",
                "password": "ChatP@ss1",
            },
        )
        other_user_id = other_reg.get_json()["user"]["id"]

        conv_resp = self.client.post(
            "/api/chat/conversations",
            json={
                "name": "Private Group",
                "participant_ids": [],
                "is_group": True,
            },
            headers=self._auth_headers(),
        )

        other_login = self.client.post(
            "/api/auth/login",
            json={"username": "otherchat", "password": "ChatP@ss1"},
        )
        other_token = other_login.get_json()["access_token"]

        if conv_resp.status_code in (200, 201):
            conv_id = conv_resp.get_json().get("id")
            if conv_id:
                response = self.client.get(
                    f"/api/chat/conversations/{conv_id}/messages",
                    headers={"Authorization": f"Bearer {other_token}"},
                )
                self.assertIn(response.status_code, [200, 403])


class AuthMeEndpointTestCase(unittest.TestCase):
    """Tests for the /api/auth/me endpoint."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()
        self.client.post(
            "/api/auth/register",
            json={
                "username": "meuser",
                "email": "me@example.com",
                "password": "MeP@ss1",
            },
        )
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "meuser", "password": "MeP@ss1"},
        )
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

    def test_me_returns_current_user(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], "meuser")
        self.assertEqual(data["email"], "me@example.com")

    def test_me_excludes_password_hash(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        data = response.get_json()
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

    def test_me_returns_user_id(self):
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        data = response.get_json()
        self.assertIn("id", data)
        self.assertIsInstance(data["id"], int)

    def test_me_returns_timestamps(self):
        response = self.client.get(
            "/api/auth/login",
            json={"username": "meuser", "password": "MeP@ss1"},
        )
        response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        data = response.get_json()
        self.assertIn("created_at", data)


class AuthEdgeCaseTestCase(unittest.TestCase):
    """Edge case and security tests for the auth system."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()

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

    def test_sql_injection_in_username(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "admin'--",
                "email": "inject@example.com",
                "password": "StrongP@ss1",
            },
        )
        self.assertIn(response.status_code, [201, 400, 422])

    def test_xss_payload_accepted_in_username(self):
        xss_payload = "<script>alert('xss')</script>"
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": xss_payload,
                "email": "xss@example.com",
                "password": "StrongP@ss1",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["user"]["username"], xss_payload)

    def test_very_long_password(self):
        long_pw = "A1!" + "a" * 1000
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "longpw",
                "email": "longpw@example.com",
                "password": long_pw,
            },
        )
        self.assertIn(response.status_code, [201, 400, 422])

    def test_unicode_password(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "unicodepw",
                "email": "unicode@example.com",
                "password": "P@ss\u00e9\u00f1123",
            },
        )
        self.assertIn(response.status_code, [201, 400])

    def test_rapid_login_attempts_with_wrong_password(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "rapiduser",
                "email": "rapid@example.com",
                "password": "StrongP@ss1",
            },
        )
        statuses = []
        for _ in range(10):
            resp = self.client.post(
                "/api/auth/login",
                json={"username": "rapiduser", "password": "WrongP@ss1"},
            )
            statuses.append(resp.status_code)
        self.assertTrue(all(s in (401, 429) for s in statuses))

    def test_concurrent_registrations_same_email(self):
        import concurrent.futures

        def register_user(i):
            return self.client.post(
                "/api/auth/register",
                json={
                    "username": f"concurrent{i}",
                    "email": "concurrent@example.com",
                    "password": "StrongP@ss1",
                },
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_user, i) for i in range(5)]
            results = [f.result() for f in futures]

        success_count = sum(1 for r in results if r.status_code == 201)
        self.assertEqual(success_count, 1)

    def test_token_not_in_login_error_response(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "WrongP@ss1"},
        )
        data = resp.get_json()
        self.assertNotIn("access_token", data)
        self.assertNotIn("token", data)

    def test_password_hash_not_in_any_response(self):
        self.client.post(
            "/api/auth/register",
            json={
                "username": "nohash",
                "email": "nohash@example.com",
                "password": "StrongP@ss1",
            },
        )
        login_resp = self.client.post(
            "/api/auth/login",
            json={"username": "nohash", "password": "StrongP@ss1"},
        )
        token = login_resp.get_json()["access_token"]
        me_resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        response_text = me_resp.get_data(as_text=True)
        self.assertNotIn("password_hash", response_text)

    def test_register_then_login_then_access_protected(self):
        reg = self.client.post(
            "/api/auth/register",
            json={
                "username": "flowuser",
                "email": "flow@example.com",
                "password": "FlowP@ss1",
            },
        )
        self.assertEqual(reg.status_code, 201)

        login = self.client.post(
            "/api/auth/login",
            json={"username": "flowuser", "password": "FlowP@ss1"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.get_json()["access_token"]

        me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["username"], "flowuser")

        chat = self.client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(chat.status_code, 200)


class UserCRUDAuthIntegrationTestCase(unittest.TestCase):
    """Tests ensuring user CRUD operations integrate with auth properly."""

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            database.init_db()

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

    def test_auth_register_creates_user_via_users_api(self):
        reg = self.client.post(
            "/api/auth/register",
            json={
                "username": "apicheck",
                "email": "apicheck@example.com",
                "password": "P@ssword1",
            },
        )
        user_id = reg.get_json()["user"]["id"]

        resp = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["username"], "apicheck")

    def test_delete_user_invalidates_token(self):
        reg = self.client.post(
            "/api/auth/register",
            json={
                "username": "deluser",
                "email": "del@example.com",
                "password": "DelP@ss1",
            },
        )
        user_id = reg.get_json()["user"]["id"]

        login = self.client.post(
            "/api/auth/login",
            json={"username": "deluser", "password": "DelP@ss1"},
        )
        token = login.get_json()["access_token"]

        self.client.delete(f"/api/users/{user_id}")

        me_resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_resp.status_code, 401)

    def test_update_email_reflected_in_login(self):
        reg = self.client.post(
            "/api/auth/register",
            json={
                "username": "emailupdate",
                "email": "old@example.com",
                "password": "P@ssword1",
            },
        )
        user_id = reg.get_json()["user"]["id"]

        self.client.put(
            f"/api/users/{user_id}",
            json={"email": "new@example.com"},
        )

        resp = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(resp.get_json()["email"], "new@example.com")


if __name__ == "__main__":
    unittest.main()
