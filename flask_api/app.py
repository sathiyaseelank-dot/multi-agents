import os
import sys

# Add the local lib directory to sys.path for Flask and dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from flask import Flask

import database
from config import DevelopmentConfig
from routes import users


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    database.init_app(app)
    app.register_blueprint(users.bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run()
