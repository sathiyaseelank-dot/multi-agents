import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Tuple

import jwt
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash

from models import User


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = User.get_by_username(username)
    if not user:
        user = User.get_by_email(username)
    if not user:
        return None
    if not check_password_hash(user.password_hash, password):
        return None
    return user


def get_current_user() -> Optional[User]:
    if hasattr(g, "current_user"):
        return g.current_user
    return None


def set_current_user(user: Optional[User]):
    g.current_user = user


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401
        
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user = User.get_by_id(payload.get("user_id"))
        if user is None:
            return jsonify({"error": "User not found"}), 401
        
        set_current_user(user)
        return f(*args, **kwargs)
    
    return decorated


def optional_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        
        if token:
            payload = decode_token(token)
            if payload:
                user = User.get_by_id(payload.get("user_id"))
                set_current_user(user)
        
        return f(*args, **kwargs)
    
    return decorated


def register_routes(app):
    from flask import Blueprint
    
    bp = Blueprint("auth", __name__, url_prefix="/api/auth")
    
    @bp.route("/register", methods=["POST"])
    def register():
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        
        if not all([username, email, password]):
            return jsonify({"error": "username, email, and password are required"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        from werkzeug.security import generate_password_hash
        
        try:
            user = User.create(username, email, generate_password_hash(password))
        except Exception as e:
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg:
                if "username" in error_msg:
                    return jsonify({"error": "Username already exists"}), 409
                elif "email" in error_msg:
                    return jsonify({"error": "Email already exists"}), 409
            return jsonify({"error": "Registration failed"}), 409
        
        token = create_access_token(user.id)
        return jsonify({
            "user": user.to_dict(),
            "access_token": token,
            "token_type": "bearer",
        }), 201
    
    @bp.route("/login", methods=["POST"])
    def login():
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        username = data.get("username")
        password = data.get("password")
        
        if not all([username, password]):
            return jsonify({"error": "username and password are required"}), 400
        
        user = authenticate_user(username, password)
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
        
        token = create_access_token(user.id)
        return jsonify({
            "user": user.to_dict(),
            "access_token": token,
            "token_type": "bearer",
        })
    
    @bp.route("/me", methods=["GET"])
    @token_required
    def get_me():
        user = get_current_user()
        return jsonify(user.to_dict())
    
    @bp.route("/refresh", methods=["POST"])
    @token_required
    def refresh():
        user = get_current_user()
        token = create_access_token(user.id)
        return jsonify({
            "access_token": token,
            "token_type": "bearer",
        })
    
    app.register_blueprint(bp)
    return bp
