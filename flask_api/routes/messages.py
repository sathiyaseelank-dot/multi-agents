from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Message, User

bp = Blueprint("messages", __name__, url_prefix="/api/messages")


@bp.route("", methods=["POST"])
@jwt_required()
def send_message():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    receiver_id = data.get("receiver_id")
    content = data.get("content")

    if not receiver_id or not content:
        return jsonify({"error": "receiver_id and content are required"}), 400

    receiver = User.get_by_id(receiver_id)
    if not receiver:
        return jsonify({"error": "Receiver not found"}), 404

    if not content.strip():
        return jsonify({"error": "Message content cannot be empty"}), 400

    message = Message.create(
        sender_id=current_user_id, receiver_id=receiver_id, content=content
    )
    return jsonify(message.to_dict()), 201


@bp.route("/conversation/<int:user_id>", methods=["GET"])
@jwt_required()
def get_conversation(user_id):
    current_user_id = int(get_jwt_identity())

    partner = User.get_by_id(user_id)
    if not partner:
        return jsonify({"error": "User not found"}), 404

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    messages = Message.get_conversation(current_user_id, user_id, limit, offset)
    return jsonify([msg.to_dict() for msg in messages]), 200


@bp.route("/conversations", methods=["GET"])
@jwt_required()
def get_conversations():
    current_user_id = int(get_jwt_identity())

    partner_ids = Message.get_conversations(current_user_id)
    conversations = []

    for partner_id in partner_ids:
        partner = User.get_by_id(partner_id)
        if partner:
            unread = Message.get_unread_count(current_user_id, partner_id)
            conversations.append(
                {
                    "user": {"id": partner.id, "username": partner.username},
                    "unread_count": unread,
                }
            )

    return jsonify(conversations), 200


@bp.route("/<int:message_id>/read", methods=["PUT"])
@jwt_required()
def mark_message_read(message_id):
    current_user_id = int(get_jwt_identity())

    message = Message.get_by_id(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.receiver_id != current_user_id:
        return jsonify({"error": "Unauthorized"}), 403

    Message.mark_as_read(message_id, current_user_id)
    return jsonify({"success": True}), 200
