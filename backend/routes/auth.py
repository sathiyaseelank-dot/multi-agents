from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime

from models import User, Session, LoginAttemptTracker
from validators import (
    EmailValidator,
    UsernameValidator,
    PasswordValidator,
    ValidationError,
)

bp = Blueprint("auth", __name__)


def error_response(error_code, message, details=None, status_code=400):
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
    }
    if details:
        response["error"]["details"] = details
    return jsonify(response), status_code


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return error_response(
                "UNAUTHORIZED",
                "Missing or invalid authorization header",
                status_code=401,
            )

        token = auth_header.split(" ", 1)[1]
        session = Session.get_by_token(token)

        if not session:
            return error_response(
                "INVALID_TOKEN", "Invalid or expired token", status_code=401
            )

        if session.token_type != "access":
            return error_response(
                "INVALID_TOKEN_TYPE", "Access token required", status_code=401
            )

        user = User.get_by_id(session.user_id)
        if not user or not user.is_active:
            return error_response(
                "USER_INACTIVE", "User account is inactive", status_code=403
            )

        request.user = user
        request.session = session
        return f(*args, **kwargs)

    return decorated


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return error_response("INVALID_REQUEST", "No data provided", status_code=400)

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    validation_errors = {}

    try:
        UsernameValidator.validate(username)
    except ValidationError as e:
        validation_errors[e.field] = e.message

    try:
        EmailValidator.validate(email)
    except ValidationError as e:
        validation_errors[e.field] = e.message

    try:
        PasswordValidator.validate(password)
    except ValidationError as e:
        validation_errors[e.field] = e.message

    if validation_errors:
        return error_response(
            "VALIDATION_ERROR",
            "Input validation failed",
            details=validation_errors,
            status_code=422,
        )

    user, create_error = User.create(username, email, password)

    if create_error:
        return error_response(
            "REGISTRATION_FAILED",
            create_error["errors"][0]
            if create_error["errors"]
            else "Registration failed",
            details=create_error["errors"],
            status_code=409,
        )

    access_token = Session.create(user.id, "access")
    refresh_token = Session.create(user.id, "refresh")

    return jsonify(
        {
            "success": True,
            "user": user.to_dict(include_email=True),
            "tokens": {
                "access_token": access_token.token,
                "refresh_token": refresh_token.token,
                "token_type": "Bearer",
                "expires_at": access_token.expires_at.isoformat(),
            },
        }
    ), 201


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return error_response("INVALID_REQUEST", "No data provided", status_code=400)

    identifier = data.get("identifier", "").strip()
    password = data.get("password", "")
    ip_address = request.remote_addr or "unknown"

    if not identifier or not password:
        return error_response(
            "VALIDATION_ERROR",
            "Identifier and password are required",
            details={
                "identifier": ["This field is required"] if not identifier else [],
                "password": ["This field is required"] if not password else [],
            },
            status_code=422,
        )

    if LoginAttemptTracker.is_locked_out(identifier, ip_address):
        return error_response(
            "ACCOUNT_LOCKED",
            "Too many failed login attempts. Please try again later.",
            details={
                "retry_after_seconds": current_app.config.get(
                    "LOGIN_LOCKOUT_DURATION", timedelta(minutes=15)
                ).seconds
            },
            status_code=429,
        )

    user = User.get_by_username(identifier) or User.get_by_email(identifier)

    if not user or not User.verify_password(user, password):
        LoginAttemptTracker.record_attempt(identifier, ip_address, successful=False)
        remaining = LoginAttemptTracker.get_remaining_attempts(identifier, ip_address)

        return error_response(
            "INVALID_CREDENTIALS",
            "Invalid username/email or password",
            details={"remaining_attempts": remaining} if remaining > 0 else None,
            status_code=401,
        )

    if not user.is_active:
        return error_response(
            "ACCOUNT_DISABLED", "This account has been disabled", status_code=403
        )

    LoginAttemptTracker.record_attempt(identifier, ip_address, successful=True)

    Session.delete_all_for_user(user.id)
    access_token = Session.create(user.id, "access")
    refresh_token = Session.create(user.id, "refresh")

    return jsonify(
        {
            "success": True,
            "user": user.to_dict(include_email=True),
            "tokens": {
                "access_token": access_token.token,
                "refresh_token": refresh_token.token,
                "token_type": "Bearer",
                "expires_at": access_token.expires_at.isoformat(),
            },
        }
    ), 200


@bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json()

    if not data:
        return error_response("INVALID_REQUEST", "No data provided", status_code=400)

    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return error_response(
            "VALIDATION_ERROR", "Refresh token is required", status_code=422
        )

    session = Session.get_by_token(refresh_token)

    if not session:
        return error_response(
            "INVALID_TOKEN", "Invalid or expired refresh token", status_code=401
        )

    if session.token_type != "refresh":
        return error_response(
            "INVALID_TOKEN_TYPE", "Refresh token required", status_code=401
        )

    user = User.get_by_id(session.user_id)
    if not user or not user.is_active:
        return error_response(
            "USER_INACTIVE", "User account is inactive", status_code=403
        )

    Session.delete_by_token(refresh_token)
    new_access_token = Session.create(user.id, "access")
    new_refresh_token = Session.create(user.id, "refresh")

    return jsonify(
        {
            "success": True,
            "tokens": {
                "access_token": new_access_token.token,
                "refresh_token": new_refresh_token.token,
                "token_type": "Bearer",
                "expires_at": new_access_token.expires_at.isoformat(),
            },
        }
    ), 200


@bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        Session.delete_by_token(token)

    return jsonify({"success": True, "message": "Successfully logged out"}), 200


@bp.route("/logout-all", methods=["POST"])
@require_auth
def logout_all():
    Session.delete_all_for_user(request.user.id)

    return jsonify(
        {"success": True, "message": "Successfully logged out from all devices"}
    ), 200


@bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    return jsonify(
        {"success": True, "user": request.user.to_dict(include_email=True)}
    ), 200


@bp.route("/verify", methods=["POST"])
@require_auth
def verify_token():
    return jsonify(
        {"success": True, "valid": True, "user": request.user.to_dict()}
    ), 200


from flask import current_app
from datetime import timedelta
