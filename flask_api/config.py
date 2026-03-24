import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    DATABASE = os.path.join(BASE_DIR, "users.db")
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DATABASE = os.path.join(BASE_DIR, "test_users.db")
