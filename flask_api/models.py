from datetime import datetime
from typing import List, Optional

from database import get_db


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
            get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
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


class Conversation:
    def __init__(self, id, name, is_group, created_at, updated_at):
        self.id = id
        self.name = name
        self.is_group = bool(is_group)
        self.created_at = created_at
        self.updated_at = updated_at
        self.participants: List[User] = []

    def to_dict(self, include_participants=False):
        data = {
            "id": self.id,
            "name": self.name,
            "is_group": self.is_group,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_participants:
            data["participants"] = [p.to_dict() for p in self.participants]
        return data

    @staticmethod
    def create(name: Optional[str] = None, is_group: bool = False) -> "Conversation":
        db = get_db()
        cursor = db.execute(
            "INSERT INTO conversations (name, is_group) VALUES (?, ?)",
            (name, is_group),
        )
        db.commit()
        return Conversation.get_by_id(cursor.lastrowid)

    @staticmethod
    def get_by_id(conversation_id) -> Optional["Conversation"]:
        row = (
            get_db()
            .execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
            .fetchone()
        )
        if row is None:
            return None
        return Conversation(**dict(row))

    @staticmethod
    def get_user_conversations(user_id: int) -> List["Conversation"]:
        rows = (
            get_db()
            .execute(
                """
                SELECT c.* FROM conversations c
                JOIN conversation_participants cp ON c.id = cp.conversation_id
                WHERE cp.user_id = ?
                ORDER BY c.updated_at DESC
                """,
                (user_id,),
            )
            .fetchall()
        )
        return [Conversation(**dict(row)) for row in rows]

    @staticmethod
    def add_participant(conversation_id: int, user_id: int) -> bool:
        try:
            db = get_db()
            db.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)",
                (conversation_id, user_id),
            )
            db.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def remove_participant(conversation_id: int, user_id: int) -> bool:
        db = get_db()
        cursor = db.execute(
            "DELETE FROM conversation_participants WHERE conversation_id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def get_participants(conversation_id: int) -> List[User]:
        rows = (
            get_db()
            .execute(
                """
                SELECT u.* FROM users u
                JOIN conversation_participants cp ON u.id = cp.user_id
                WHERE cp.conversation_id = ?
                """,
                (conversation_id,),
            )
            .fetchall()
        )
        return [User(**dict(row)) for row in rows]

    @staticmethod
    def is_participant(conversation_id: int, user_id: int) -> bool:
        row = (
            get_db()
            .execute(
                "SELECT 1 FROM conversation_participants WHERE conversation_id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
            .fetchone()
        )
        return row is not None

    def load_participants(self):
        self.participants = Conversation.get_participants(self.id)
        return self


class Message:
    def __init__(self, id, conversation_id, sender_id, content, message_type, is_read, created_at, updated_at, sender=None):
        self.id = id
        self.conversation_id = conversation_id
        self.sender_id = sender_id
        self.content = content
        self.message_type = message_type
        self.is_read = bool(is_read)
        self.created_at = created_at
        self.updated_at = updated_at
        self.sender = sender

    def to_dict(self, include_sender=False):
        data = {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "content": self.content,
            "message_type": self.message_type,
            "is_read": self.is_read,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_sender and self.sender:
            data["sender"] = self.sender.to_dict()
        return data

    @staticmethod
    def create(conversation_id: int, sender_id: int, content: str, message_type: str = "text") -> "Message":
        db = get_db()
        cursor = db.execute(
            "INSERT INTO messages (conversation_id, sender_id, content, message_type) VALUES (?, ?, ?, ?)",
            (conversation_id, sender_id, content, message_type),
        )
        db.commit()
        
        db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        db.commit()
        
        return Message.get_by_id(cursor.lastrowid)

    @staticmethod
    def get_by_id(message_id: int) -> Optional["Message"]:
        row = (
            get_db()
            .execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            .fetchone()
        )
        if row is None:
            return None
        message = Message(**dict(row))
        message.sender = User.get_by_id(message.sender_id)
        return message

    @staticmethod
    def get_conversation_messages(
        conversation_id: int,
        limit: int = 50,
        before_id: Optional[int] = None
    ) -> List["Message"]:
        if before_id:
            rows = (
                get_db()
                .execute(
                    """
                    SELECT * FROM messages
                    WHERE conversation_id = ? AND id < ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (conversation_id, before_id, limit),
                )
                .fetchall()
            )
        else:
            rows = (
                get_db()
                .execute(
                    """
                    SELECT * FROM messages
                    WHERE conversation_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (conversation_id, limit),
                )
                .fetchall()
            )
        
        messages = []
        for row in rows:
            message = Message(**dict(row))
            message.sender = User.get_by_id(message.sender_id)
            messages.append(message)
        return list(reversed(messages))

    @staticmethod
    def mark_as_read(message_id: int) -> Optional["Message"]:
        db = get_db()
        db.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,))
        db.commit()
        return Message.get_by_id(message_id)

    @staticmethod
    def mark_conversation_read(conversation_id: int, user_id: int) -> int:
        db = get_db()
        cursor = db.execute(
            """
            UPDATE messages
            SET is_read = 1
            WHERE conversation_id = ? AND sender_id != ? AND is_read = 0
            """,
            (conversation_id, user_id),
        )
        db.commit()
        return cursor.rowcount

    @staticmethod
    def get_unread_count(conversation_id: int, user_id: int) -> int:
        row = (
            get_db()
            .execute(
                """
                SELECT COUNT(*) as count FROM messages
                WHERE conversation_id = ? AND sender_id != ? AND is_read = 0
                """,
                (conversation_id, user_id),
            )
            .fetchone()
        )
        return row["count"] if row else 0

    @staticmethod
    def delete(message_id: int) -> bool:
        db = get_db()
        cursor = db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        db.commit()
        return cursor.rowcount > 0

    @staticmethod
    def update(message_id: int, content: str) -> Optional["Message"]:
        db = get_db()
        db.execute(
            "UPDATE messages SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (content, message_id),
        )
        db.commit()
        return Message.get_by_id(message_id)
