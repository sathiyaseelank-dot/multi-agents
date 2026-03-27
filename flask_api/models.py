from database import get_db
from datetime import datetime


class User:
    def __init__(self, id, username, email, password_hash, created_at, updated_at):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def create(username, email, password_hash):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        db.commit()
        return User.get_by_id(cursor.lastrowid)

    @staticmethod
    def get_by_id(user_id):
        row = (
            get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))

    @staticmethod
    def get_all():
        rows = get_db().execute("SELECT * FROM users ORDER BY id").fetchall()
        return [User(**dict(row)) for row in rows]

    @staticmethod
    def update(user_id, **kwargs):
        allowed = {"username", "email", "password_hash"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return User.get_by_id(user_id)
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]
        db = get_db()
        db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        db.commit()
        return User.get_by_id(user_id)

    @staticmethod
    def delete(user_id):
        db = get_db()
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()

    @staticmethod
    def get_by_username(username):
        row = (
            get_db()
            .execute("SELECT * FROM users WHERE username = ?", (username,))
            .fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))

    @staticmethod
    def get_by_email(email):
        row = (
            get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))


class Message:
    def __init__(self, id, sender_id, receiver_id, content, created_at, is_read):
        self.id = id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.content = content
        self.created_at = created_at
        self.is_read = bool(is_read)

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
            "is_read": self.is_read,
        }

    @staticmethod
    def create(sender_id, receiver_id, content):
        db = get_db()
        cursor = db.execute(
            "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (sender_id, receiver_id, content),
        )
        db.commit()
        return Message.get_by_id(cursor.lastrowid)

    @staticmethod
    def get_by_id(message_id):
        row = (
            get_db()
            .execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            .fetchone()
        )
        if row is None:
            return None
        return Message(**dict(row))

    @staticmethod
    def get_conversation(user1_id, user2_id, limit=50, offset=0):
        rows = (
            get_db()
            .execute(
                """SELECT * FROM messages 
               WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (user1_id, user2_id, user2_id, user1_id, limit, offset),
            )
            .fetchall()
        )
        return [Message(**dict(row)) for row in rows]

    @staticmethod
    def get_conversations(user_id):
        rows = (
            get_db()
            .execute(
                """SELECT DISTINCT 
               CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as partner_id
               FROM messages 
               WHERE sender_id = ? OR receiver_id = ?
               ORDER BY (SELECT MAX(created_at) FROM messages 
                        WHERE (sender_id = ? AND receiver_id = partner_id) 
                           OR (sender_id = partner_id AND receiver_id = ?)) DESC""",
                (user_id, user_id, user_id, user_id, user_id),
            )
            .fetchall()
        )
        return [row["partner_id"] for row in rows]

    @staticmethod
    def mark_as_read(message_id, user_id):
        db = get_db()
        db.execute(
            "UPDATE messages SET is_read = 1 WHERE id = ? AND receiver_id = ?",
            (message_id, user_id),
        )
        db.commit()

    @staticmethod
    def get_unread_count(user_id, partner_id):
        row = (
            get_db()
            .execute(
                """SELECT COUNT(*) as count FROM messages 
               WHERE sender_id = ? AND receiver_id = ? AND is_read = 0""",
                (partner_id, user_id),
            )
            .fetchone()
        )
        return row["count"] if row else 0
