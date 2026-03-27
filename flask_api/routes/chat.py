from flask import Blueprint, jsonify, request

from auth import token_required, get_current_user
from database import get_db
from models import Message, Conversation, User

bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@bp.route("/conversations", methods=["GET"])
@token_required
def get_conversations():
    user = get_current_user()
    conversations = Conversation.get_user_conversations(user.id)
    
    result = []
    for conv in conversations:
        conv.load_participants()
        conv_data = conv.to_dict(include_participants=True)
        conv_data["unread_count"] = Message.get_unread_count(conv.id, user.id)
        last_message = Message.get_conversation_messages(conv.id, limit=1)
        if last_message:
            conv_data["last_message"] = last_message[0].to_dict(include_sender=True)
        result.append(conv_data)
    
    return jsonify(result)


@bp.route("/conversations", methods=["POST"])
@token_required
def create_conversation():
    user = get_current_user()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    participant_ids = data.get("participant_ids", [])
    is_group = data.get("is_group", False)
    name = data.get("name")
    
    if not isinstance(participant_ids, list):
        return jsonify({"error": "participant_ids must be a list"}), 400
    
    if is_group and not name:
        return jsonify({"error": "Group name is required for group conversations"}), 400
    
    if not is_group and len(participant_ids) != 1:
        return jsonify({"error": "Direct conversations require exactly 1 other participant"}), 400
    
    existing_ids = set(participant_ids)
    existing_ids.add(user.id)
    
    if not is_group:
        existing_conv = _find_direct_conversation(user.id, participant_ids[0])
        if existing_conv:
            existing_conv.load_participants()
            return jsonify(existing_conv.to_dict(include_participants=True))
    
    conversation = Conversation.create(name=name, is_group=is_group)
    conversation.add_participant(user.id, user.id)
    
    for pid in participant_ids:
        if pid != user.id:
            conversation.add_participant(conversation.id, pid)
    
    conversation.load_participants()
    return jsonify(conversation.to_dict(include_participants=True)), 201


@bp.route("/conversations/<int:conversation_id>", methods=["GET"])
@token_required
def get_conversation(conversation_id):
    user = get_current_user()
    
    if not Conversation.is_participant(conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    conversation = Conversation.get_by_id(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    conversation.load_participants()
    return jsonify(conversation.to_dict(include_participants=True))


@bp.route("/conversations/<int:conversation_id>/participants", methods=["POST"])
@token_required
def add_participant(conversation_id):
    user = get_current_user()
    data = request.get_json()
    
    if not Conversation.is_participant(conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    conversation = Conversation.get_by_id(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    if not conversation.is_group:
        return jsonify({"error": "Cannot add participants to direct conversations"}), 400
    
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    if Conversation.is_participant(conversation_id, user_id):
        return jsonify({"error": "User is already a participant"}), 409
    
    if conversation.add_participant(conversation_id, user_id):
        return jsonify({"message": "Participant added"})
    return jsonify({"error": "Failed to add participant"}), 500


@bp.route("/conversations/<int:conversation_id>/participants/<int:user_id>", methods=["DELETE"])
@token_required
def remove_participant(conversation_id, user_id):
    current_user = get_current_user()
    
    if not Conversation.is_participant(conversation_id, current_user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    conversation = Conversation.get_by_id(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404
    
    if user_id != current_user.id and not conversation.is_group:
        return jsonify({"error": "Cannot remove participants from direct conversations"}), 400
    
    if Conversation.remove_participant(conversation_id, user_id):
        return jsonify({"message": "Participant removed"})
    return jsonify({"error": "Failed to remove participant"}), 500


def _find_direct_conversation(user_id1, user_id2):
    rows = (
        get_db()
        .execute(
            """
            SELECT c.id FROM conversations c
            JOIN conversation_participants cp1 ON c.id = cp1.conversation_id AND cp1.user_id = ?
            JOIN conversation_participants cp2 ON c.id = cp2.conversation_id AND cp2.user_id = ?
            WHERE c.is_group = 0
            """,
            (user_id1, user_id2),
        )
        .fetchone()
    )
    if rows:
        return Conversation.get_by_id(rows["id"])
    return None


@bp.route("/conversations/<int:conversation_id>/messages", methods=["GET"])
@token_required
def get_messages(conversation_id):
    user = get_current_user()
    
    if not Conversation.is_participant(conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    limit = request.args.get("limit", 50, type=int)
    before_id = request.args.get("before", type=int)
    
    limit = min(limit, 100)
    messages = Message.get_conversation_messages(conversation_id, limit=limit, before_id=before_id)
    
    Message.mark_conversation_read(conversation_id, user.id)
    
    return jsonify([m.to_dict(include_sender=True) for m in messages])


@bp.route("/conversations/<int:conversation_id>/messages", methods=["POST"])
@token_required
def send_message(conversation_id):
    user = get_current_user()
    
    if not Conversation.is_participant(conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    content = data.get("content")
    message_type = data.get("message_type", "text")
    
    if not content:
        return jsonify({"error": "content is required"}), 400
    
    if len(content) > 10000:
        return jsonify({"error": "Message content too long (max 10000 characters)"}), 400
    
    valid_types = ["text", "image", "file", "system"]
    if message_type not in valid_types:
        return jsonify({"error": f"Invalid message_type. Must be one of: {valid_types}"}), 400
    
    message = Message.create(
        conversation_id=conversation_id,
        sender_id=user.id,
        content=content,
        message_type=message_type,
    )
    
    return jsonify(message.to_dict(include_sender=True)), 201


@bp.route("/messages/<int:message_id>", methods=["GET"])
@token_required
def get_message(message_id):
    user = get_current_user()
    message = Message.get_by_id(message_id)
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    if not Conversation.is_participant(message.conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    return jsonify(message.to_dict(include_sender=True))


@bp.route("/messages/<int:message_id>", methods=["PUT"])
@token_required
def update_message(message_id):
    user = get_current_user()
    message = Message.get_by_id(message_id)
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    if message.sender_id != user.id:
        return jsonify({"error": "Can only edit your own messages"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    content = data.get("content")
    if not content:
        return jsonify({"error": "content is required"}), 400
    
    if len(content) > 10000:
        return jsonify({"error": "Message content too long (max 10000 characters)"}), 400
    
    updated_message = Message.update(message_id, content)
    return jsonify(updated_message.to_dict(include_sender=True))


@bp.route("/messages/<int:message_id>", methods=["DELETE"])
@token_required
def delete_message(message_id):
    user = get_current_user()
    message = Message.get_by_id(message_id)
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    if message.sender_id != user.id:
        return jsonify({"error": "Can only delete your own messages"}), 403
    
    if Message.delete(message_id):
        return jsonify({"message": "Message deleted"})
    return jsonify({"error": "Failed to delete message"}), 500


@bp.route("/messages/<int:message_id>/read", methods=["POST"])
@token_required
def mark_message_read(message_id):
    user = get_current_user()
    message = Message.get_by_id(message_id)
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    if not Conversation.is_participant(message.conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    updated_message = Message.mark_as_read(message_id)
    return jsonify(updated_message.to_dict(include_sender=True))


@bp.route("/conversations/<int:conversation_id>/read", methods=["POST"])
@token_required
def mark_conversation_read(conversation_id):
    user = get_current_user()
    
    if not Conversation.is_participant(conversation_id, user.id):
        return jsonify({"error": "Not a participant of this conversation"}), 403
    
    count = Message.mark_conversation_read(conversation_id, user.id)
    return jsonify({"marked_read": count})


@bp.route("/users/search", methods=["GET"])
@token_required
def search_users():
    query = request.args.get("q", "")
    if len(query) < 2:
        return jsonify({"error": "Search query must be at least 2 characters"}), 400
    
    rows = (
        get_db()
        .execute(
            """
            SELECT * FROM users
            WHERE username LIKE ? OR email LIKE ?
            LIMIT 20
            """,
            (f"%{query}%", f"%{query}%"),
        )
        .fetchall()
    )
    
    users = [User(**dict(row)).to_dict() for row in rows]
    return jsonify(users)
