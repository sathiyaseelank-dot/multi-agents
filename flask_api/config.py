import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    DATABASE = os.path.join(BASE_DIR, "users.db")
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(24)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or os.urandom(24)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{os.path.join(BASE_DIR, 'users.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_HEADERS = "Content-Type"
    SOCKETIO_MESSAGE_QUEUE = None
    SOCKETIO_ASYNC_MODE = "threading"


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = os.path.join(BASE_DIR, "test_users.db")
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    DEBUG = False
    SOCKETIO_MESSAGE_QUEUE = os.environ.get("SOCKETIO_MESSAGE_QUEUE")
