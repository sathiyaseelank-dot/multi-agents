import secrets
import sqlite3
import bcrypt
from datetime import datetime, timedelta
from flask import current_app
from database import get_db
from validators import (
    PasswordValidator,
    EmailValidator,
    UsernameValidator,
    ValidationError,
)


class User:
    def __init__(
        self, id, username, email, password_hash, is_active, created_at, updated_at
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_active = bool(is_active)
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self, include_email=False):
        data = {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_email:
            data["email"] = self.email
        return data

    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt(rounds=current_app.config.get("BCRYPT_LOG_ROUNDS", 12))
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(user, password):
        return bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        )

    @staticmethod
    def create(username, email, password):
        try:
            UsernameValidator.validate(username)
            EmailValidator.validate(email)
            PasswordValidator.validate(password)
        except ValidationError as e:
            return None, {"field": e.field, "errors": e.message}

        password_hash = User.hash_password(password)
        db = get_db()

        try:
            cursor = db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return None, {
                "field": "general",
                "errors": ["Username or email already exists"],
            }

        return User.get_by_id(cursor.lastrowid), None

    @staticmethod
    def get_by_id(user_id):
        row = (
            get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))

    @staticmethod
    def get_by_username(username):
        row = (
            get_db()
            .execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
            )
            .fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))

    @staticmethod
    def get_by_email(email):
        row = (
            get_db()
            .execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,))
            .fetchone()
        )
        if row is None:
            return None
        return User(**dict(row))


class Session:
    def __init__(self, id, user_id, token, token_type, expires_at, created_at):
        self.id = id
        self.user_id = user_id
        self.token = token
        self.token_type = token_type
        self.expires_at = expires_at
        self.created_at = created_at

    def to_dict(self):
        return {
            "token": self.token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def is_expired(self):
        return datetime.now() > self.expires_at

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def create(user_id, token_type="access"):
        token = Session.generate_token()
        expires_delta = (
            current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
            if token_type == "access"
            else current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        )
        expires_at = datetime.now() + expires_delta

        db = get_db()
        cursor = db.execute(
            "INSERT INTO sessions (user_id, token, token_type, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, token, token_type, expires_at),
        )
        db.commit()
        return Session.get_by_token(token)

    @staticmethod
    def get_by_token(token):
        row = (
            get_db()
            .execute(
                "SELECT * FROM sessions WHERE token = ? AND expires_at > ?",
                (token, datetime.now()),
            )
            .fetchone()
        )
        if row is None:
            return None
        return Session(**dict(row))

    @staticmethod
    def delete_by_token(token):
        db = get_db()
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        db.commit()

    @staticmethod
    def delete_expired():
        db = get_db()
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(),))
        db.commit()

    @staticmethod
    def delete_all_for_user(user_id):
        db = get_db()
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        db.commit()


class LoginAttemptTracker:
    @staticmethod
    def record_attempt(identifier, ip_address, successful=False):
        db = get_db()
        db.execute(
            "INSERT INTO login_attempts (identifier, ip_address, successful) VALUES (?, ?, ?)",
            (identifier, ip_address, 1 if successful else 0),
        )
        db.commit()

    @staticmethod
    def is_locked_out(identifier, ip_address):
        max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
        lockout_duration = current_app.config.get(
            "LOGIN_LOCKOUT_DURATION", timedelta(minutes=15)
        )
        cutoff_time = datetime.now() - lockout_duration

        db = get_db()
        recent_attempts = db.execute(
            """SELECT COUNT(*) as count FROM login_attempts 
               WHERE (identifier = ? OR ip_address = ?) 
               AND attempted_at > ? AND successful = 0""",
            (identifier, ip_address, cutoff_time),
        ).fetchone()

        return recent_attempts["count"] >= max_attempts

    @staticmethod
    def get_remaining_attempts(identifier, ip_address):
        max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)
        lockout_duration = current_app.config.get(
            "LOGIN_LOCKOUT_DURATION", timedelta(minutes=15)
        )
        cutoff_time = datetime.now() - lockout_duration

        db = get_db()
        recent_attempts = db.execute(
            """SELECT COUNT(*) as count FROM login_attempts 
               WHERE (identifier = ? OR ip_address = ?) 
               AND attempted_at > ? AND successful = 0""",
            (identifier, ip_address, cutoff_time),
        ).fetchone()

        remaining = max_attempts - recent_attempts["count"]
        return max(0, remaining)
