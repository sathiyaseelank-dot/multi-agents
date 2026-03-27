from flask_socketio import emit, join_room, leave_room
from flask_jwt_extended import decode_token
from flask import request

active_users = {}


def init_socketio(socketio):

    @socketio.on("connect")
    def handle_connect():
        token = request.args.get("token")
        if not token:
            emit("error", {"message": "Authentication required"})
            return False

        try:
            decoded = decode_token(token)
            user_id = decoded["sub"]
            active_users[request.sid] = {"user_id": user_id, "sid": request.sid}
            join_room(f"user_{user_id}")
            emit("connected", {"status": "connected", "user_id": user_id})
        except Exception as e:
            emit("error", {"message": str(e)})
            return False

    @socketio.on("disconnect")
    def handle_disconnect():
        if request.sid in active_users:
            user_id = active_users[request.sid]["user_id"]
            del active_users[request.sid]
            leave_room(f"user_{user_id}")

    @socketio.on("send_message")
    def handle_send_message(data):
        if request.sid not in active_users:
            emit("error", {"message": "Not authenticated"})
            return

        user_id = active_users[request.sid]["user_id"]
        receiver_id = data.get("receiver_id")
        content = data.get("content")

        if not receiver_id or not content:
            emit("error", {"message": "receiver_id and content required"})
            return

        from models import Message

        message = Message.create(
            sender_id=user_id, receiver_id=receiver_id, content=content
        )

        emit(
            "new_message",
            message.to_dict(),
            room=f"user_{receiver_id}",
            include_self=False,
        )
        emit("message_sent", message.to_dict())

    @socketio.on("typing")
    def handle_typing(data):
        if request.sid not in active_users:
            return

        user_id = active_users[request.sid]["user_id"]
        receiver_id = data.get("receiver_id")

        if receiver_id:
            emit(
                "user_typing",
                {"user_id": user_id},
                room=f"user_{receiver_id}",
                include_self=False,
            )

    @socketio.on("join_room")
    def handle_join_room(data):
        room = data.get("room")
        if room:
            join_room(room)
            emit("joined_room", {"room": room})

    @socketio.on("leave_room")
    def handle_leave_room(data):
        room = data.get("room")
        if room:
            leave_room(room)
            emit("left_room", {"room": room})
