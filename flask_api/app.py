import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from flask import Flask, render_template
from flask_cors import CORS

import database
from config import DevelopmentConfig
from routes import users, orchestrator_api, analytics
from routes.chat import bp as chat_bp
from auth import register_routes
from sockets import init_socketio


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)
    
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    database.init_app(app)
    app.register_blueprint(users.bp)
    app.register_blueprint(orchestrator_api.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(chat_bp)
    register_routes(app)
    
    init_socketio(app)
    
    return app


if __name__ == "__main__":
    app = create_app()
    from sockets import socketio
    socketio.run(app, debug=True, use_reloader=False, host="0.0.0.0", port=5000)
