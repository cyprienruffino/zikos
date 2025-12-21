"""Tests for Chat service"""

from unittest.mock import MagicMock, patch

import pytest

from zikos.services.chat import ChatService


@pytest.fixture
def mock_backend():
    """Mock LLM backend"""
    backend = MagicMock()
    backend.is_initialized.return_value = True
    backend.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Test response", "role": "assistant"}}]
    }
    return backend


@pytest.fixture
def chat_service(mock_backend):
    """Create ChatService instance with mocked LLM"""
    with patch("zikos.services.llm.create_backend", return_value=mock_backend):
        with patch("zikos.services.llm.settings") as mock_settings:
            mock_settings.llm_model_path = ""
            service = ChatService()
            service.llm_service.backend = mock_backend
            yield service


class TestChatService:
    """Tests for ChatService"""

    def test_initialization(self, chat_service):
        """Test chat service initialization"""
        assert chat_service.llm_service is not None
        assert chat_service.mcp_server is not None
        assert isinstance(chat_service.sessions, dict)
        assert len(chat_service.sessions) == 0

    def test_create_session(self, chat_service):
        """Test session creation"""
        session_id = chat_service._create_session()

        assert isinstance(session_id, str)
        assert len(session_id) > 0
        assert session_id in chat_service.sessions
        assert chat_service.sessions[session_id] == {"messages": []}

    def test_create_session_unique(self, chat_service):
        """Test that each session gets a unique ID"""
        session_id1 = chat_service._create_session()
        session_id2 = chat_service._create_session()

        assert session_id1 != session_id2
        assert len(chat_service.sessions) == 2

    @pytest.mark.asyncio
    async def test_process_message_without_session(self, chat_service):
        """Test processing message without existing session"""
        result = await chat_service.process_message("Hello")

        assert "session_id" in result
        assert result["session_id"] in chat_service.sessions
        assert "type" in result

    @pytest.mark.asyncio
    async def test_process_message_with_session(self, chat_service):
        """Test processing message with existing session"""
        session_id = chat_service._create_session()

        result = await chat_service.process_message("Hello", session_id)

        assert result["session_id"] == session_id
        assert "type" in result

    @pytest.mark.asyncio
    async def test_handle_audio_ready(self, chat_service, temp_dir):
        """Test handling audio ready notification"""
        import uuid
        from pathlib import Path

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        result = await chat_service.handle_audio_ready(audio_file_id, "recording1", "session1")

        assert "type" in result
        assert result["type"] == "response"
        assert "audio_file_id" in result
        assert result["audio_file_id"] == audio_file_id
        assert "message" in result

    @pytest.mark.asyncio
    async def test_handle_audio_ready_without_session(self, chat_service, temp_dir):
        """Test handling audio ready without session ID"""
        import uuid
        from pathlib import Path

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        result = await chat_service.handle_audio_ready(audio_file_id, "recording1", None)

        assert "type" in result
        assert result["type"] == "response"
        assert "audio_file_id" in result

    @pytest.mark.asyncio
    async def test_disconnect(self, chat_service):
        """Test WebSocket disconnect handling"""
        from unittest.mock import MagicMock

        from fastapi import WebSocket

        mock_websocket = MagicMock(spec=WebSocket)
        await chat_service.disconnect(mock_websocket)

        assert True
