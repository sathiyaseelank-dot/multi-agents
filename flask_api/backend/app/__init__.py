from flask import Flask
from flask_jwt_extended import JWTManager
from app.config import Config
from app.models import db, bcrypt
from app.auth import auth_bp
from app.messages import messages_bp
from app.analytics import analytics_bp
from app.hi import hi_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(hi_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return {"status": "healthy"}, 200

    with app.app_context():
        db.create_all()

    return app
