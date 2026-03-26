import os
import sys
import sqlite3
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flask_api", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flask_api"))

from flask import Flask
from config import TestingConfig
import database


class DatabaseConnectionTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        database.init_app(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_get_db_returns_connection(self):
        with self.app.app_context():
            db = database.get_db()
            self.assertIsNotNone(db)
            self.assertIsInstance(db, sqlite3.Connection)

    def test_get_db_returns_same_connection_in_same_context(self):
        with self.app.app_context():
            db1 = database.get_db()
            db2 = database.get_db()
            self.assertIs(db1, db2)

    def test_db_has_row_factory(self):
        with self.app.app_context():
            db = database.get_db()
            self.assertEqual(db.row_factory, sqlite3.Row)

    def test_close_db_removes_connection(self):
        with self.app.app_context():
            db = database.get_db()
            self.assertIsNotNone(db)
            database.close_db()
            self.assertNotIn("db", database.g)

    def test_close_db_handles_no_connection(self):
        with self.app.app_context():
            database.close_db()

    def test_database_file_created(self):
        self.assertTrue(os.path.exists(self.app.config["DATABASE"]))


class DatabaseConfigTestCase(unittest.TestCase):
    def test_testing_config_database_path(self):
        from config import TestingConfig

        self.assertTrue(TestingConfig.DATABASE.endswith("test_users.db"))
        self.assertTrue(TestingConfig.TESTING)

    def test_development_config_debug(self):
        from config import DevelopmentConfig

        self.assertTrue(DevelopmentConfig.DEBUG)
        self.assertFalse(DevelopmentConfig.TESTING)

    def test_base_config_defaults(self):
        from config import Config

        self.assertFalse(Config.DEBUG)
        self.assertFalse(Config.TESTING)
        self.assertTrue(Config.DATABASE.endswith("users.db"))


class DatabaseSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        database.init_app(self.app)

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_users_table_exists(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)

    def test_users_table_columns(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA table_info(users)")
            columns = {row[1] for row in cursor.fetchall()}
            expected = {
                "id",
                "username",
                "email",
                "password_hash",
                "created_at",
                "updated_at",
            }
            self.assertEqual(columns, expected)

    def test_users_table_unique_constraints(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
            )
            schema = cursor.fetchone()[0].upper()
            self.assertIn("UNIQUE", schema)

    def test_timestamp_trigger_exists(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND name='update_users_timestamp'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)


class DatabaseExtendedSchemaTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        database.init_app(self.app)
        self._create_extended_tables()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_extended_tables(self):
        with self.app.app_context():
            db = database.get_db()
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

                CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON auth_tokens(user_id);
                CREATE INDEX IF NOT EXISTS idx_auth_tokens_token ON auth_tokens(token);
                CREATE INDEX IF NOT EXISTS idx_conversations_created_by ON conversations(created_by);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id);
                CREATE INDEX IF NOT EXISTS idx_conversation_members_user_id ON conversation_members(user_id);
            """)
            db.commit()

    def test_auth_tokens_table_exists(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='auth_tokens'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_auth_tokens_columns(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA table_info(auth_tokens)")
            columns = {row[1] for row in cursor.fetchall()}
            expected = {
                "id",
                "user_id",
                "token",
                "token_type",
                "expires_at",
                "created_at",
                "revoked",
            }
            self.assertEqual(columns, expected)

    def test_conversations_table_exists(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_conversations_columns(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA table_info(conversations)")
            columns = {row[1] for row in cursor.fetchall()}
            expected = {"id", "name", "type", "created_by", "created_at", "updated_at"}
            self.assertEqual(columns, expected)

    def test_messages_table_exists(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_messages_columns(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA table_info(messages)")
            columns = {row[1] for row in cursor.fetchall()}
            expected = {
                "id",
                "conversation_id",
                "sender_id",
                "content",
                "message_type",
                "created_at",
                "updated_at",
                "deleted_at",
            }
            self.assertEqual(columns, expected)

    def test_conversation_members_table_exists(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_members'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_foreign_key_auth_tokens_to_users(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA foreign_key_list(auth_tokens)")
            fks = cursor.fetchall()
            self.assertTrue(any(row[2] == "users" for row in fks))

    def test_foreign_key_conversations_to_users(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA foreign_key_list(conversations)")
            fks = cursor.fetchall()
            self.assertTrue(any(row[2] == "users" for row in fks))

    def test_foreign_key_messages_to_conversations(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA foreign_key_list(messages)")
            fks = cursor.fetchall()
            self.assertTrue(any(row[2] == "conversations" for row in fks))

    def test_foreign_key_messages_to_users(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute("PRAGMA foreign_key_list(messages)")
            fks = cursor.fetchall()
            self.assertTrue(any(row[2] == "users" for row in fks))

    def test_indexes_exist(self):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
            expected = {
                "idx_auth_tokens_user_id",
                "idx_auth_tokens_token",
                "idx_conversations_created_by",
                "idx_messages_conversation_id",
                "idx_messages_sender_id",
                "idx_conversation_members_user_id",
            }
            for idx in expected:
                self.assertIn(idx, indexes)


class DatabaseCRUDTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig)
        self.app.config["TESTING"] = True
        database.init_app(self.app)
        self._create_extended_tables()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_extended_tables(self):
        with self.app.app_context():
            db = database.get_db()
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

    def _insert_user(
        self, username="testuser", email="test@example.com", password_hash="hashed"
    ):
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            db.commit()
            return cursor.lastrowid

    def test_insert_and_retrieve_auth_token(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            db.execute(
                "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, "test-token-abc", "2099-12-31T23:59:59"),
            )
            db.commit()
            cursor = db.execute(
                "SELECT * FROM auth_tokens WHERE token = ?", ("test-token-abc",)
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["user_id"], user_id)
            self.assertEqual(row["revoked"], 0)

    def test_revoke_auth_token(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            db.execute(
                "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, "revoke-token", "2099-12-31T23:59:59"),
            )
            db.commit()
            db.execute(
                "UPDATE auth_tokens SET revoked = 1 WHERE token = ?", ("revoke-token",)
            )
            db.commit()
            cursor = db.execute(
                "SELECT revoked FROM auth_tokens WHERE token = ?", ("revoke-token",)
            )
            self.assertEqual(cursor.fetchone()["revoked"], 1)

    def test_insert_and_retrieve_conversation(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "INSERT INTO conversations (name, type, created_by) VALUES (?, ?, ?)",
                ("Test Room", "group", user_id),
            )
            db.commit()
            conv_id = cursor.lastrowid
            cursor = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["name"], "Test Room")
            self.assertEqual(row["type"], "group")

    def test_conversation_member_management(self):
        user_id = self._insert_user()
        user2_id = self._insert_user("user2", "user2@example.com")
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "INSERT INTO conversations (name, created_by) VALUES (?, ?)",
                ("Room", user_id),
            )
            conv_id = cursor.lastrowid
            db.execute(
                "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                (conv_id, user_id),
            )
            db.execute(
                "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
                (conv_id, user2_id),
            )
            db.commit()
            cursor = db.execute(
                "SELECT COUNT(*) as cnt FROM conversation_members WHERE conversation_id = ?",
                (conv_id,),
            )
            self.assertEqual(cursor.fetchone()["cnt"], 2)

    def test_insert_and_retrieve_message(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)",
                (user_id,),
            )
            conv_id = cursor.lastrowid
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user_id, "Hello, world!"),
            )
            db.commit()
            cursor = db.execute(
                "SELECT * FROM messages WHERE conversation_id = ?", (conv_id,)
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["content"], "Hello, world!")
            self.assertEqual(row["sender_id"], user_id)

    def test_message_ordering(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)", (user_id,)
            )
            conv_id = cursor.lastrowid
            for i in range(5):
                db.execute(
                    "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                    (conv_id, user_id, f"Message {i}"),
                )
            db.commit()
            cursor = db.execute(
                "SELECT content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conv_id,),
            )
            messages = [row["content"] for row in cursor.fetchall()]
            self.assertEqual(messages, [f"Message {i}" for i in range(5)])

    def test_soft_delete_message(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            cursor = db.execute(
                "INSERT INTO conversations (created_by) VALUES (?)", (user_id,)
            )
            conv_id = cursor.lastrowid
            db.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (?, ?, ?)",
                (conv_id, user_id, "To be deleted"),
            )
            db.commit()
            msg_id = (
                cursor.lastrowid
                if hasattr(cursor, "lastrowid")
                else db.execute("SELECT last_insert_rowid()").fetchone()[0]
            )
            db.execute(
                "UPDATE messages SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                (msg_id,),
            )
            db.commit()
            cursor = db.execute(
                "SELECT deleted_at FROM messages WHERE id = ?", (msg_id,)
            )
            self.assertIsNotNone(cursor.fetchone()["deleted_at"])

    def test_cascade_delete_user_removes_tokens(self):
        user_id = self._insert_user()
        with self.app.app_context():
            db = database.get_db()
            db.execute(
                "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, "cascade-token", "2099-12-31"),
            )
            db.commit()
            db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            db.commit()
            cursor = db.execute(
                "SELECT * FROM auth_tokens WHERE user_id = ?", (user_id,)
            )
            self.assertIsNone(cursor.fetchone())


if __name__ == "__main__":
    unittest.main()
