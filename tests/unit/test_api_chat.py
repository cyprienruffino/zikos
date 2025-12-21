"""Unit tests for chat API endpoints"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from zikos.api.chat import router
from zikos.main import app

app.include_router(router, prefix="/api/chat")


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Mock chat service"""
    with patch("zikos.api.chat.chat_service") as mock:
        mock.process_message = AsyncMock()
        mock.handle_audio_ready = AsyncMock()
        mock.get_thinking = Mock()
        mock.disconnect = AsyncMock()
        yield mock


class TestChatAPI:
    """Tests for chat API endpoints"""

    def test_websocket_message(self, client, mock_chat_service):
        """Test WebSocket message handling"""
        from unittest.mock import AsyncMock

        mock_chat_service.process_message.return_value = {
            "type": "response",
            "message": "Hello back",
            "session_id": "test_session",
        }

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "message", "message": "Hello"})

            response = websocket.receive_json()

            assert "type" in response
            assert response["type"] == "response"
            mock_chat_service.process_message.assert_called_once()

    def test_websocket_message_with_session(self, client, mock_chat_service):
        """Test WebSocket message with session ID"""
        mock_chat_service.process_message.return_value = {
            "type": "response",
            "session_id": "test_session",
        }

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {"type": "message", "message": "Hello", "session_id": "test_session"}
            )

            response = websocket.receive_json()
            assert "session_id" in response

    def test_websocket_audio_ready(self, client, mock_chat_service):
        """Test WebSocket audio ready handling"""
        mock_chat_service.handle_audio_ready.return_value = {
            "type": "response",
            "audio_file_id": "test_audio",
            "recording_id": "test_recording",
        }

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "audio_ready",
                    "audio_file_id": "test_audio",
                    "recording_id": "test_recording",
                    "session_id": "test_session",
                }
            )

            response = websocket.receive_json()
            assert response["type"] == "response"
            assert response["audio_file_id"] == "test_audio"

    def test_websocket_cancel_recording(self, client):
        """Test WebSocket cancel recording"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "cancel_recording", "recording_id": "test_recording"})

            response = websocket.receive_json()
            assert response["type"] == "recording_cancelled"
            assert response["recording_id"] == "test_recording"

    def test_websocket_disconnect(self, client, mock_chat_service):
        """Test WebSocket disconnect handling"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.close()

        mock_chat_service.disconnect.assert_called_once()

    def test_websocket_message_error_handling(self, client, mock_chat_service):
        """Test error handling when process_message raises exception"""
        mock_chat_service.process_message.side_effect = Exception("Processing error")

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "message", "message": "Hello"})

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Error processing message" in response["message"]

    def test_websocket_audio_ready_error_handling(self, client, mock_chat_service):
        """Test error handling when handle_audio_ready raises exception"""
        mock_chat_service.handle_audio_ready.side_effect = Exception("Audio error")

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "audio_ready",
                    "audio_file_id": "test_audio",
                    "recording_id": "test_recording",
                }
            )

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Error handling audio" in response["message"]

    def test_websocket_get_thinking(self, client, mock_chat_service):
        """Test WebSocket get_thinking handling"""
        mock_chat_service.get_thinking.return_value = {
            "type": "thinking",
            "thinking": [{"thinking": "Test thinking", "position": 0}],
        }

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "get_thinking", "session_id": "test_session"})

            response = websocket.receive_json()
            assert response["type"] == "thinking"

    def test_websocket_get_thinking_error_handling(self, client, mock_chat_service):
        """Test error handling when get_thinking raises exception"""
        mock_chat_service.get_thinking.side_effect = Exception("Thinking error")

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "get_thinking", "session_id": "test_session"})

            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Error getting thinking" in response["message"]
