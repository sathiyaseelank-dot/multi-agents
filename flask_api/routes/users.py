from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from models import User

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = User.get_by_username(username)
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": access_token, "user": user.to_dict()}), 200


@bp.route("", methods=["GET"])
@jwt_required()
def get_users():
    users = User.get_all()
    return jsonify([u.to_dict() for u in users])


@bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = User.get_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())


@bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
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
@jwt_required()
def update_user(user_id):
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403
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
@jwt_required()
def delete_user(user_id):
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    if User.get_by_id(user_id) is None:
        return jsonify({"error": "User not found"}), 404
    User.delete(user_id)
    return jsonify({"message": "User deleted"}), 200
