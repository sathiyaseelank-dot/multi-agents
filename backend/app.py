import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from flask_cors import CORS

from config import DevelopmentConfig
from database import init_app


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    init_app(app)

    from routes import auth, health, calculator

    app.register_blueprint(auth.bp, url_prefix="/api/auth")
    app.register_blueprint(health.bp, url_prefix="/api")
    app.register_blueprint(calculator.bp, url_prefix="/api/calculator")

    @app.route("/api/health")
    def health_check():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
