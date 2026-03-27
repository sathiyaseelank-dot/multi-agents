from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User

hi_bp = Blueprint("hi", __name__, url_prefix="/api/hi")


def validate_name(name):
    if not name:
        return "Name is required"
    if not isinstance(name, str):
        return "Name must be a string"
    name = name.strip()
    if len(name) < 1:
        return "Name cannot be empty"
    if len(name) > 100:
        return "Name must be 100 characters or less"
    return None


@hi_bp.route("", methods=["POST"])
@jwt_required()
def create_hi():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if data is None:
        return jsonify({"error": "No data provided"}), 400

    name = data.get("name")
    validation_error = validate_name(name)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    name = name.strip()

    return jsonify({"message": f"Hi, {name}!", "user_id": current_user_id}), 201


@hi_bp.route("", methods=["GET"])
@jwt_required()
def get_hi():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    username = user.username

    return jsonify(
        {
            "message": f"Hi, {username}!",
            "user_id": current_user_id,
            "username": username,
        }
    ), 200


@hi_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "hi"}), 200
