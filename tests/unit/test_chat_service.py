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
        from unittest.mock import AsyncMock

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        # Mock generate_response to return a successful response
        chat_service.llm_service.generate_response = AsyncMock(
            return_value={"type": "response", "message": "Audio analysis complete"}
        )

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

        # Mock generate_response to return a successful response
        from unittest.mock import AsyncMock

        chat_service.llm_service.generate_response = AsyncMock(
            return_value={"type": "response", "message": "Audio analysis complete"}
        )

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

    @pytest.mark.asyncio
    async def test_process_message_stream_creates_session(self, chat_service):
        """Test streaming creates session if none provided"""

        # Mock the LLM service to return streaming tokens
        async def mock_stream(*args, **kwargs):
            yield {"type": "token", "content": "Hello"}
            yield {"type": "token", "content": " there"}
            yield {"type": "response", "message": "Hello there"}

        chat_service.llm_service.generate_response_stream = mock_stream

        tokens = []
        session_found = False
        async for chunk in chat_service.process_message_stream("Hello"):
            if chunk.get("type") == "token":
                tokens.append(chunk.get("content", ""))
            elif chunk.get("type") == "session_id":
                assert "session_id" in chunk
                session_found = True

        assert len(tokens) > 0
        assert session_found

    @pytest.mark.asyncio
    async def test_process_message_stream_handles_llm_error(self, chat_service):
        """Test streaming handles LLM service errors"""

        async def error_stream(*args, **kwargs):
            yield {"type": "error", "message": "LLM error"}

        chat_service.llm_service.generate_response_stream = error_stream

        chunks = []
        async for chunk in chat_service.process_message_stream("Hello", "test_session"):
            chunks.append(chunk)

        error_chunks = [c for c in chunks if c.get("type") == "error"]
        assert len(error_chunks) > 0

    @pytest.mark.asyncio
    async def test_process_message_stream_preserves_session_id(self, chat_service):
        """Test streaming preserves session ID in all chunks"""
        session_id = chat_service._create_session()
        chunks = []
        async for chunk in chat_service.process_message_stream("Hello", session_id):
            chunks.append(chunk)
            assert chunk.get("session_id") == session_id

    def test_get_thinking_without_session_id(self, chat_service):
        """Test get_thinking returns error when session_id is None"""
        result = chat_service.get_thinking(None)

        assert "error" in result
        assert result["error"] == "session_id required"

    def test_get_thinking_with_session_id(self, chat_service):
        """Test get_thinking with valid session_id"""
        session_id = chat_service._create_session()
        chat_service.llm_service.get_thinking_for_session = MagicMock(
            return_value=[{"thinking": "Test", "position": 0}]
        )

        result = chat_service.get_thinking(session_id)

        assert "thinking" in result
        assert isinstance(result["thinking"], list)

    @pytest.mark.asyncio
    async def test_handle_audio_ready_with_string_response(self, chat_service, temp_dir):
        """Test handle_audio_ready when LLM service returns string instead of dict"""
        import uuid
        from pathlib import Path
        from unittest.mock import AsyncMock

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        chat_service.llm_service.handle_audio_ready = AsyncMock(
            return_value="Audio analysis complete"
        )

        result = await chat_service.handle_audio_ready(audio_file_id, "recording1", "session1")

        assert "type" in result
        assert result["type"] == "response"
        assert "audio_file_id" in result
        assert result["audio_file_id"] == audio_file_id
        assert "message" in result
        assert result["message"] == "Audio analysis complete"

    @pytest.mark.asyncio
    async def test_handle_audio_ready_with_empty_response(self, chat_service, temp_dir):
        """Test handle_audio_ready when LLM service returns empty response"""
        import uuid
        from pathlib import Path
        from unittest.mock import AsyncMock

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        chat_service.llm_service.handle_audio_ready = AsyncMock(return_value=None)

        result = await chat_service.handle_audio_ready(audio_file_id, "recording1", "session1")

        assert "type" in result
        assert result["type"] == "response"
        assert "audio_file_id" in result
        assert "message" in result
        assert result["message"] == "Audio analysis complete."

    @pytest.mark.asyncio
    async def test_handle_audio_ready_with_exception(self, chat_service, temp_dir):
        """Test handle_audio_ready when LLM service raises exception"""
        import uuid
        from pathlib import Path
        from unittest.mock import AsyncMock

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        audio_path = Path(settings.audio_storage_path) / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        chat_service.llm_service.handle_audio_ready = AsyncMock(
            side_effect=Exception("Processing error")
        )

        result = await chat_service.handle_audio_ready(audio_file_id, "recording1", "session1")

        assert "type" in result
        assert result["type"] == "error"
        assert "audio_file_id" in result
        assert result["audio_file_id"] == audio_file_id
        assert "Error processing audio" in result["message"]
