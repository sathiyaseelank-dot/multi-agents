import re
from datetime import datetime, timedelta
from database import get_db


class ValidationError(Exception):
    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(message)


class PasswordValidator:
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    @classmethod
    def validate(cls, password):
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must not exceed {cls.MAX_LENGTH} characters")
        if cls.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        if cls.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        if cls.REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append(
                f"Password must contain at least one special character ({cls.SPECIAL_CHARS})"
            )

        if errors:
            raise ValidationError("password", errors)


class EmailValidator:
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    @classmethod
    def validate(cls, email):
        if not email:
            raise ValidationError("email", ["Email is required"])
        if not cls.EMAIL_REGEX.match(email):
            raise ValidationError("email", ["Invalid email format"])
        if len(email) > 255:
            raise ValidationError("email", ["Email must not exceed 255 characters"])


class UsernameValidator:
    MIN_LENGTH = 3
    MAX_LENGTH = 32
    USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")

    @classmethod
    def validate(cls, username):
        errors = []

        if not username:
            errors.append("Username is required")
        elif len(username) < cls.MIN_LENGTH:
            errors.append(f"Username must be at least {cls.MIN_LENGTH} characters long")
        elif len(username) > cls.MAX_LENGTH:
            errors.append(f"Username must not exceed {cls.MAX_LENGTH} characters")
        elif not cls.USERNAME_REGEX.match(username):
            errors.append(
                "Username can only contain letters, numbers, hyphens, and underscores"
            )

        if errors:
            raise ValidationError("username", errors)
