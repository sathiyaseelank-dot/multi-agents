import os
import sys

# Add the flask_api directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))
# Add the local lib directory to sys.path for Flask and dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from flask import Flask
from flask_cors import CORS

import database
from config import DevelopmentConfig
from routes import users, orchestrator_api


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for frontend access
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    database.init_app(app)
    app.register_blueprint(users.bp)
    app.register_blueprint(orchestrator_api.bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
