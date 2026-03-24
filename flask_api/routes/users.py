from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from models import User

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.route("", methods=["GET"])
def get_users():
    users = User.get_all()
    return jsonify([u.to_dict() for u in users])


@bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.get_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())


@bp.route("", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not all([username, email, password]):
        return jsonify({"error": "username, email, and password are required"}), 400
    password_hash = generate_password_hash(password)
    try:
        user = User.create(username, email, password_hash)
    except Exception as e:
        return jsonify({"error": str(e)}), 409
    return jsonify(user.to_dict()), 201


@bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    if User.get_by_id(user_id) is None:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    if "password" in data:
        data["password_hash"] = generate_password_hash(data.pop("password"))
    user = User.update(user_id, **data)
    return jsonify(user.to_dict())


@bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if User.get_by_id(user_id) is None:
        return jsonify({"error": "User not found"}), 404
    User.delete(user_id)
    return jsonify({"message": "User deleted"}), 200
