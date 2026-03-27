import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request

from auth import decode_token, get_current_user
from models import Message, Conversation, User

logger = logging.getLogger(__name__)

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


connected_users = {}


def init_socketio(app):
    socketio.init_app(app)
    return socketio


def authenticate_socket(token: str):
    payload = decode_token(token)
    if payload:
        user = User.get_by_id(payload.get("user_id"))
        return user
    return None


@socketio.on("connect")
def handle_connect():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        emit("error", {"message": "Authentication required"})
        return False
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        emit("error", {"message": "Invalid authorization header"})
        return False
    
    user = authenticate_socket(parts[1])
    if not user:
        emit("error", {"message": "Invalid token"})
        return False
    
    connected_users[request.sid] = {"user_id": user.id, "username": user.username}
    emit("connected", {"user_id": user.id, "sid": request.sid})
    logger.info(f"User {user.username} connected with sid {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    if request.sid in connected_users:
        user_info = connected_users.pop(request.sid)
        logger.info(f"User {user_info['username']} disconnected")


@socketio.on("join")
def handle_join(data):
    user_sid = request.sid
    if user_sid not in connected_users:
        emit("error", {"message": "Not authenticated"})
        return
    
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        emit("error", {"message": "conversation_id is required"})
        return
    
    user_id = connected_users[user_sid]["user_id"]
    
    if not Conversation.is_participant(conversation_id, user_id):
        emit("error", {"message": "Not a participant of this conversation"})
        return
    
    join_room(f"conversation_{conversation_id}")
    emit("joined", {"conversation_id": conversation_id})
    logger.info(f"User {connected_users[user_sid]['username']} joined conversation {conversation_id}")


@socketio.on("leave")
def handle_leave(data):
    conversation_id = data.get("conversation_id")
    if conversation_id:
        leave_room(f"conversation_{conversation_id}")
        emit("left", {"conversation_id": conversation_id})


@socketio.on("message")
def handle_message(data):
    user_sid = request.sid
    if user_sid not in connected_users:
        emit("error", {"message": "Not authenticated"})
        return
    
    user_id = connected_users[user_sid]["user_id"]
    conversation_id = data.get("conversation_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    
    if not conversation_id or not content:
        emit("error", {"message": "conversation_id and content are required"})
        return
    
    if not Conversation.is_participant(conversation_id, user_id):
        emit("error", {"message": "Not a participant of this conversation"})
        return
    
    if len(content) > 10000:
        emit("error", {"message": "Message content too long"})
        return
    
    message = Message.create(
        conversation_id=conversation_id,
        sender_id=user_id,
        content=content,
        message_type=message_type,
    )
    
    message_data = message.to_dict(include_sender=True)
    emit("message", message_data)
    emit("message", message_data, room=f"conversation_{conversation_id}")


@socketio.on("typing")
def handle_typing(data):
    user_sid = request.sid
    if user_sid not in connected_users:
        return
    
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    
    user_id = connected_users[user_sid]["user_id"]
    username = connected_users[user_sid]["username"]
    
    emit(
        "typing",
        {"user_id": user_id, "username": username},
        room=f"conversation_{conversation_id}",
        include_self=False,
    )


@socketio.on("stop_typing")
def handle_stop_typing(data):
    user_sid = request.sid
    if user_sid not in connected_users:
        return
    
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    
    user_id = connected_users[user_sid]["user_id"]
    
    emit(
        "stop_typing",
        {"user_id": user_id},
        room=f"conversation_{conversation_id}",
        include_self=False,
    )


@socketio.on("read")
def handle_read(data):
    user_sid = request.sid
    if user_sid not in connected_users:
        return
    
    user_id = connected_users[user_sid]["user_id"]
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return
    
    if not Conversation.is_participant(conversation_id, user_id):
        return
    
    count = Message.mark_conversation_read(conversation_id, user_id)
    
    emit(
        "read",
        {"conversation_id": conversation_id, "user_id": user_id, "count": count},
        room=f"conversation_{conversation_id}",
    )


@socketio.on("get_online_users")
def handle_get_online_users():
    online = [{"sid": sid, **info} for sid, info in connected_users.items()]
    emit("online_users", online)


def emit_new_message(conversation_id, message):
    message_data = message.to_dict(include_sender=True)
    socketio.emit("message", message_data, room=f"conversation_{conversation_id}")


def emit_user_typing(conversation_id, user_id, username):
    socketio.emit(
        "typing",
        {"user_id": user_id, "username": username},
        room=f"conversation_{conversation_id}",
        include_self=False,
    )


def emit_user_read(conversation_id, user_id):
    socketio.emit(
        "read",
        {"conversation_id": conversation_id, "user_id": user_id},
        room=f"conversation_{conversation_id}",
        include_self=False,
    )
