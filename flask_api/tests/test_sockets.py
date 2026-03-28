import pytest
from unittest.mock import patch, MagicMock
from flask_socketio import SocketIOTestClient

from app import create_app
from sockets import connected_users


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def socketio(app):
    from sockets import socketio as _socketio
    return _socketio


class TestWebSocketAuthentication:
    def test_connect_without_token(self, app, socketio):
        with app.test_client() as client:
            with patch('sockets.emit') as mock_emit:
                with client.socketio.on('connect'):
                    mock_emit.assert_called_with('error', {'message': 'Authentication required'})

    def test_connect_with_invalid_token(self, app, socketio):
        with app.test_request_context():
            from flask import request
            with patch('sockets.emit') as mock_emit:
                pass

    def test_emit_connected_event(self, app):
        with app.test_client() as client:
            with patch('sockets.emit') as mock_emit:
                mock_emit.return_value = None
                client.socketio.emit('message', {'conversation_id': 1})


class TestWebSocketEvents:
    def test_connected_users_tracking(self, app, socketio):
        with app.test_request_context():
            initial_count = len(connected_users)
            assert initial_count == 0

    def test_message_event_validation(self, app):
        with app.test_request_context():
            from sockets import handle_message
            with patch('sockets.emit') as mock_emit:
                mock_emit.reset_mock()
                handle_message({'content': 'test'})
                mock_emit.assert_called()

    def test_typing_event(self, app):
        with app.test_request_context():
            from sockets import handle_typing
            with patch('sockets.emit') as mock_emit:
                handle_typing({'conversation_id': 1})
                mock_emit.assert_called()


class TestSocketIOMessageBroadcasting:
    def test_emit_new_message_function(self, app):
        from sockets import emit_new_message
        from models import Message
        from unittest.mock import MagicMock
        
        mock_message = MagicMock(spec=Message)
        mock_message.to_dict.return_value = {'id': 1, 'content': 'test'}
        
        with app.test_request_context():
            from sockets import socketio
            with patch.object(socketio, 'emit') as mock_emit:
                emit_new_message(1, mock_message)
                mock_emit.assert_called_once()


class TestOnlineUsers:
    def test_get_online_users(self, app):
        with app.test_request_context():
            from sockets import handle_get_online_users, connected_users
            with patch('sockets.emit') as mock_emit:
                handle_get_online_users()
                mock_emit.assert_called()

    def test_emit_user_typing(self, app):
        with app.test_request_context():
            from sockets import emit_user_typing
            with patch('sockets.emit') as mock_emit:
                emit_user_typing(1, 1, 'testuser')
                mock_emit.assert_called_once()

    def test_emit_user_read(self, app):
        with app.test_request_context():
            from sockets import emit_user_read
            with patch('sockets.emit') as mock_emit:
                emit_user_read(1, 1)
                mock_emit.assert_called_once()
