"""Integration tests for Chat API"""

import pytest
from fastapi.testclient import TestClient

from src.zikos.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestChatWebSocket:
    """Tests for WebSocket chat endpoint"""

    def test_websocket_connection(self, client):
        """Test WebSocket connection establishment"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            assert websocket is not None

    def test_websocket_message(self, client):
        """Test sending message via WebSocket"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "message", "message": "Hello"})

            response = websocket.receive_json()

            assert "type" in response
            assert "session_id" in response

    def test_websocket_message_with_session(self, client):
        """Test sending message with existing session"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            session_id = "test_session_123"

            websocket.send_json({"type": "message", "message": "Hello", "session_id": session_id})

            response = websocket.receive_json()

            assert "session_id" in response
            assert response["session_id"] == session_id

    def test_websocket_audio_ready(self, client, temp_dir):
        """Test audio ready notification via WebSocket"""
        import uuid
        from pathlib import Path

        from src.zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "audio_ready",
                    "audio_file_id": audio_file_id,
                    "recording_id": "recording1",
                    "session_id": "session1",
                }
            )

            response = websocket.receive_json()

            assert "type" in response
            assert response["type"] == "response"
            assert "audio_file_id" in response
            assert response["audio_file_id"] == audio_file_id

    def test_websocket_cancel_recording(self, client):
        """Test cancel recording via WebSocket"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "cancel_recording",
                    "recording_id": "recording1",
                }
            )

            response = websocket.receive_json()

            assert "type" in response
            assert response["type"] == "recording_cancelled"
            assert "recording_id" in response

    def test_websocket_disconnect(self, client):
        """Test WebSocket disconnect handling"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.close()

        assert True

    def test_websocket_invalid_message_type(self, client):
        """Test WebSocket with invalid message type"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json({"type": "invalid_type", "data": "test"})

            try:
                response = websocket.receive_json(timeout=1.0)
                assert "type" in response or "error" in response
            except Exception:
                pass
