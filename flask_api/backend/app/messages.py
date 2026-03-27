from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Message, User
from datetime import datetime, timedelta

messages_bp = Blueprint("messages", __name__, url_prefix="/api/messages")


@messages_bp.route("", methods=["GET"])
@jwt_required()
def get_messages():
    limit = request.args.get("limit", 50, type=int)
    before = request.args.get("before", type=int)

    query = Message.query

    if before:
        query = query.filter(Message.id < before)

    messages = query.order_by(Message.created_at.desc()).limit(limit).all()

    return jsonify([msg.to_dict() for msg in reversed(messages)]), 200


@messages_bp.route("", methods=["POST"])
@jwt_required()
def create_message():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "Message content is required"}), 400

    if len(content) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)"}), 400

    message = Message(content=content, user_id=current_user_id)
    db.session.add(message)
    db.session.commit()

    return jsonify(message.to_dict()), 201


@messages_bp.route("/<int:message_id>", methods=["DELETE"])
@jwt_required()
def delete_message(message_id):
    current_user_id = get_jwt_identity()
    message = Message.query.get(message_id)

    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.user_id != current_user_id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(message)
    db.session.commit()

    return jsonify({"message": "Message deleted"}), 200
