import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flask_api", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flask_api"))

from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash

from config import TestingConfig
from database import get_db, close_db, init_db, init_app
from models import User


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        init_app(self.app)

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_user_create(self):
        with self.app.app_context():
            password_hash = generate_password_hash("password123")
            user = User.create("testuser", "test@example.com", password_hash)
            self.assertIsNotNone(user)
            self.assertEqual(user.username, "testuser")
            self.assertEqual(user.email, "test@example.com")
            self.assertIsNotNone(user.id)
            self.assertIsNotNone(user.created_at)

    def test_user_to_dict_excludes_password(self):
        with self.app.app_context():
            password_hash = generate_password_hash("secret")
            user = User.create("testuser", "test@example.com", password_hash)
            user_dict = user.to_dict()
            self.assertNotIn("password_hash", user_dict)
            self.assertIn("id", user_dict)
            self.assertIn("username", user_dict)
            self.assertIn("email", user_dict)
            self.assertIn("created_at", user_dict)
            self.assertIn("updated_at", user_dict)

    def test_user_get_by_id(self):
        with self.app.app_context():
            password_hash = generate_password_hash("pass")
            created = User.create("getbyid", "getbyid@example.com", password_hash)
            fetched = User.get_by_id(created.id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.username, "getbyid")

    def test_user_get_by_id_not_found(self):
        with self.app.app_context():
            user = User.get_by_id(99999)
            self.assertIsNone(user)

    def test_user_get_all_empty(self):
        with self.app.app_context():
            users = User.get_all()
            self.assertEqual(users, [])

    def test_user_get_all_returns_all(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            User.create("user1", "u1@example.com", ph)
            User.create("user2", "u2@example.com", ph)
            User.create("user3", "u3@example.com", ph)
            users = User.get_all()
            self.assertEqual(len(users), 3)
            names = {u.username for u in users}
            self.assertEqual(names, {"user1", "user2", "user3"})

    def test_user_update_username(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            user = User.create("oldname", "upd@example.com", ph)
            updated = User.update(user.id, username="newname")
            self.assertEqual(updated.username, "newname")
            self.assertEqual(updated.email, "upd@example.com")

    def test_user_update_email(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            user = User.create("updemail", "old@example.com", ph)
            updated = User.update(user.id, email="new@example.com")
            self.assertEqual(updated.email, "new@example.com")

    def test_user_update_password(self):
        with self.app.app_context():
            ph = generate_password_hash("oldpass")
            user = User.create("updpass", "pass@example.com", ph)
            new_hash = generate_password_hash("newpass")
            updated = User.update(user.id, password_hash=new_hash)
            self.assertNotEqual(updated.password_hash, ph)

    def test_user_update_no_valid_fields(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            user = User.create("nofields", "nf@example.com", ph)
            updated = User.update(user.id, invalid_field="value")
            self.assertEqual(updated.username, "nofields")

    def test_user_update_none_values_ignored(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            user = User.create("noneval", "nv@example.com", ph)
            updated = User.update(user.id, username=None, email=None)
            self.assertEqual(updated.username, "noneval")
            self.assertEqual(updated.email, "nv@example.com")

    def test_user_delete(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            user = User.create("deleteme", "del@example.com", ph)
            User.delete(user.id)
            self.assertIsNone(User.get_by_id(user.id))

    def test_user_delete_nonexistent(self):
        with self.app.app_context():
            User.delete(99999)

    def test_user_unique_username(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            User.create("unique_user", "u1@example.com", ph)
            with self.assertRaises(Exception):
                User.create("unique_user", "u2@example.com", ph)

    def test_user_unique_email(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            User.create("user_a", "shared@example.com", ph)
            with self.assertRaises(Exception):
                User.create("user_b", "shared@example.com", ph)

    def test_user_password_verification(self):
        with self.app.app_context():
            password = "mysecretpassword"
            ph = generate_password_hash(password)
            user = User.create("pwcheck", "pw@example.com", ph)
            self.assertTrue(check_password_hash(user.password_hash, password))
            self.assertFalse(check_password_hash(user.password_hash, "wrongpassword"))

    def test_user_create_returns_complete_user(self):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            user = User.create("complete", "comp@example.com", ph)
            self.assertIsNotNone(user.id)
            self.assertEqual(user.username, "complete")
            self.assertEqual(user.email, "comp@example.com")
            self.assertIsNotNone(user.password_hash)
            self.assertIsNotNone(user.created_at)
            self.assertIsNotNone(user.updated_at)


class AuthTokenModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        init_app(self.app)
        self._create_auth_table()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM auth_tokens")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_auth_table(self):
        with self.app.app_context():
            db = get_db()
            db.executescript("""
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    token_type TEXT NOT NULL DEFAULT 'bearer',
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
            db.commit()

    def _create_user(self, username="authuser", email="auth@example.com"):
        with self.app.app_context():
            ph = generate_password_hash("pass")
            return User.create(username, email, ph)

    def _create_token(self, user_id, token="test-token", expires_hours=24):
        expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires_at),
            )
            db.commit()
            cursor = db.execute("SELECT * FROM auth_tokens WHERE token = ?", (token,))
            return dict(cursor.fetchone())

    def test_auth_token_create(self):
        user = self._create_user()
        token_data = self._create_token(user.id, "new-token")
        self.assertIsNotNone(token_data["id"])
        self.assertEqual(token_data["user_id"], user.id)
        self.assertEqual(token_data["token"], "new-token")
        self.assertEqual(token_data["revoked"], 0)

    def test_auth_token_default_type(self):
        user = self._create_user()
        token_data = self._create_token(user.id, "type-token")
        self.assertEqual(token_data["token_type"], "bearer")

    def test_auth_token_unique(self):
        user = self._create_user()
        self._create_token(user.id, "unique-token")
        with self.assertRaises(Exception):
            self._create_token(user.id, "unique-token")

    def test_auth_token_revoke(self):
        user = self._create_user()
        self._create_token(user.id, "rev-token")
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE auth_tokens SET revoked = 1 WHERE token = ?", ("rev-token",)
            )
            db.commit()
            cursor = db.execute(
                "SELECT revoked FROM auth_tokens WHERE token = ?", ("rev-token",)
            )
            self.assertEqual(cursor.fetchone()["revoked"], 1)

    def test_auth_token_expiry(self):
        user = self._create_user()
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user.id, "expired-token", past),
            )
            db.commit()
            cursor = db.execute(
                "SELECT * FROM auth_tokens WHERE token = ? AND expires_at < CURRENT_TIMESTAMP",
                ("expired-token",),
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_auth_token_cascade_delete_on_user_removal(self):
        user = self._create_user()
        self._create_token(user.id, "cascade-tok")
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM users WHERE id = ?", (user.id,))
            db.commit()
            cursor = db.execute(
                "SELECT * FROM auth_tokens WHERE token = ?", ("cascade-tok",)
            )
            self.assertIsNone(cursor.fetchone())

    def test_auth_token_multiple_per_user(self):
        user = self._create_user()
        self._create_token(user.id, "tok-1")
        self._create_token(user.id, "tok-2")
        self._create_token(user.id, "tok-3")
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "SELECT COUNT(*) as cnt FROM auth_tokens WHERE user_id = ?", (user.id,)
            )
            self.assertEqual(cursor.fetchone()["cnt"], 3)


class ConversationModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        init_app(self.app)
        self._create_conversation_tables()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM conversation_members")
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_conversation_tables(self):
        with self.app.app_context():
            db = get_db()
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT NOT NULL DEFAULT 'direct',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS conversation_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(conversation_id, user_id)
                );
            """)
            db.commit()

    def _create_user(self, username="convuser", email="conv@example.com"):
        with self.app.app_context():
            return User.create(username, email, generate_password_hash("pass"))

    def test_conversation_create(self):
        user = self._create_user()
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO conversations (name, type, created_by) VALUES (?, ?, ?)",
                ("My Room", "group", user.id),
            )
            db.commit()
            cursor = db.execute(
                "SELECT * FROM conversations WHERE id = ?", (cursor.lastrowid,)
            )
            conv = cursor.fetchone()
            self.assertIsNotNone(conv)
            self.assertEqual(conv["name"], "My Room")
            self.assertEqual(conv["type"], "group")
            self.assertEqual(conv["created_by"], user.id)

    def test_conversation_default_type_direct(self):
        user = self._create_user()
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)",
                (user.id,),
            )
            db.commit()
            cursor = db.execute(
                "SELECT type FROM conversations WHERE id = ?", (cursor.lastrowid,)
            )
            self.assertEqual(cursor.fetchone()["type"], "direct")

    def test_conversation_members_add(self):
        user1 = self._create_user("u1", "u1@example.com")
        user2 = self._create_user("u2", "u2@example.com")
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)", (user1.id,)
            )
            conv_id = cursor.lastrowid
            db.execute(
                "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                (conv_id, user1.id),
            )
            db.execute(
                "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                (conv_id, user2.id),
            )
            db.commit()
            cursor = db.execute(
                "SELECT COUNT(*) as cnt FROM conversation_members WHERE conversation_id = ?",
                (conv_id,),
            )
            self.assertEqual(cursor.fetchone()["cnt"], 2)

    def test_conversation_member_unique_constraint(self):
        user = self._create_user()
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)", (user.id,)
            )
            conv_id = cursor.lastrowid
            db.execute(
                "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                (conv_id, user.id),
            )
            db.commit()
            with self.assertRaises(Exception):
                db.execute(
                    "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                    (conv_id, user.id),
                )

    def test_conversation_list_user_conversations(self):
        user1 = self._create_user("listu1", "lu1@example.com")
        user2 = self._create_user("listu2", "lu2@example.com")
        with self.app.app_context():
            db = get_db()
            for name in ["Room A", "Room B", "Room C"]:
                cursor = db.execute(
                    "INSERT INTO conversations (name, created_by) VALUES (?, ?)",
                    (name, user1.id),
                )
                db.execute(
                    "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                    (cursor.lastrowid, user1.id),
                )
                db.execute(
                    "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                    (cursor.lastrowid, user2.id),
                )
            db.commit()
            cursor = db.execute(
                "SELECT c.* FROM conversations c "
                "JOIN conversation_members cm ON c.id = cm.conversation_id "
                "WHERE cm.user_id = ?",
                (user1.id,),
            )
            rooms = cursor.fetchall()
            self.assertEqual(len(rooms), 3)

    def test_conversation_cascade_delete_on_user_removal(self):
        user = self._create_user("cascadeu", "cascade@example.com")
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)", (user.id,)
            )
            conv_id = cursor.lastrowid
            db.commit()
            db.execute("DELETE FROM users WHERE id = ?", (user.id,))
            db.commit()
            cursor = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
            self.assertIsNone(cursor.fetchone())


class MessageModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        init_app(self.app)
        self._create_message_tables()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM conversations")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_message_tables(self):
        with self.app.app_context():
            db = get_db()
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT NOT NULL DEFAULT 'direct',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    sender_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL DEFAULT 'text',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
            db.commit()

    def _create_user(self, username="msguser", email="msg@example.com"):
        with self.app.app_context():
            return User.create(username, email, generate_password_hash("pass"))

    def _create_conversation(self, user_id):
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)", (user_id,)
            )
            db.commit()
            return cursor.lastrowid

    def test_message_create(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user.id, "Hello!"),
            )
            db.commit()
            cursor = db.execute(
                "SELECT * FROM messages WHERE conversation_id = ?", (conv_id,)
            )
            msg = cursor.fetchone()
            self.assertIsNotNone(msg)
            self.assertEqual(msg["content"], "Hello!")
            self.assertEqual(msg["sender_id"], user.id)
            self.assertEqual(msg["message_type"], "text")

    def test_message_default_type_text(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user.id, "type test"),
            )
            db.commit()
            cursor = db.execute(
                "SELECT message_type FROM messages WHERE content = 'type test'"
            )
            self.assertEqual(cursor.fetchone()["message_type"], "text")

    def test_message_chronological_order(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            for i in range(10):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                    (conv_id, user.id, f"msg-{i}"),
                )
            db.commit()
            cursor = db.execute(
                "SELECT content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conv_id,),
            )
            contents = [r["content"] for r in cursor.fetchall()]
            self.assertEqual(contents, [f"msg-{i}" for i in range(10)])

    def test_message_soft_delete(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            cursor = db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user.id, "soft delete me"),
            )
            msg_id = cursor.lastrowid
            db.execute(
                "UPDATE messages SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                (msg_id,),
            )
            db.commit()
            cursor = db.execute(
                "SELECT deleted_at FROM messages WHERE id = ?", (msg_id,)
            )
            self.assertIsNotNone(cursor.fetchone()["deleted_at"])

    def test_message_filter_deleted(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            for i in range(5):
                cursor = db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                    (conv_id, user.id, f"msg-{i}"),
                )
            # Soft delete first message
            db.execute(
                "UPDATE messages SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                (cursor.lastrowid,),
            )
            db.commit()
            cursor = db.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ? AND deleted_at IS NULL",
                (conv_id,),
            )
            active = cursor.fetchone()["cnt"]
            self.assertEqual(active, 4)

    def test_message_multiple_senders(self):
        user1 = self._create_user("sender1", "s1@example.com")
        user2 = self._create_user("sender2", "s2@example.com")
        conv_id = self._create_conversation(user1.id)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user1.id, "From user 1"),
            )
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user2.id, "From user 2"),
            )
            db.commit()
            cursor = db.execute(
                "SELECT DISTINCT sender_id FROM messages WHERE conversation_id = ?",
                (conv_id,),
            )
            senders = {r["sender_id"] for r in cursor.fetchall()}
            self.assertEqual(senders, {user1.id, user2.id})

    def test_message_pagination(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            for i in range(25):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                    (conv_id, user.id, f"msg-{i:02d}"),
                )
            db.commit()
            cursor = db.execute(
                "SELECT content FROM messages WHERE conversation_id = ? "
                "ORDER BY created_at DESC LIMIT 10 OFFSET 5",
                (conv_id,),
            )
            page = cursor.fetchall()
            self.assertEqual(len(page), 10)

    def test_message_cascade_delete_on_conversation_removal(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user.id, "cascade msg"),
            )
            db.commit()
            db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            db.commit()
            cursor = db.execute(
                "SELECT * FROM messages WHERE conversation_id = ?", (conv_id,)
            )
            self.assertIsNone(cursor.fetchone())

    def test_message_content_not_empty(self):
        user = self._create_user()
        conv_id = self._create_conversation(user.id)
        with self.app.app_context():
            db = get_db()
            with self.assertRaises(Exception):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                    (conv_id, user.id, None),
                )


if __name__ == "__main__":
    unittest.main()
