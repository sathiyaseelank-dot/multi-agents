import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

import database
from config import DevelopmentConfig
from routes import users, messages, orchestrator_api, hi
from socket_events import init_socketio

socketio = SocketIO()
jwt = JWTManager()


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    database.init_app(app)
    app.register_blueprint(users.bp)
    app.register_blueprint(messages.bp)
    app.register_blueprint(orchestrator_api.bp)
    app.register_blueprint(hi.bp)

    init_socketio(socketio)

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(
        app,
        debug=True,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True,
        use_reloader=False,
    )
