"""Unit tests for Chat service streaming functionality"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.services.chat import ChatService


@pytest.fixture
def mock_backend_with_streaming():
    """Mock LLM backend with streaming support"""
    backend = MagicMock()
    backend.is_initialized.return_value = True

    async def stream_chat_completion(*args, **kwargs):
        tokens = ["Hello", " there", "!", " How", " can", " I", " help", "?"]
        for token in tokens:
            yield {
                "choices": [
                    {"delta": {"content": token, "role": "assistant"}, "finish_reason": None}
                ]
            }
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

    backend.stream_chat_completion = stream_chat_completion
    backend.get_cached_system_prompt.return_value = None
    return backend


@pytest.fixture
def chat_service_streaming(mock_backend_with_streaming):
    """Create ChatService instance with mocked streaming LLM"""
    with patch("zikos.services.llm.create_backend", return_value=mock_backend_with_streaming):
        with patch("zikos.services.llm.settings") as mock_settings:
            mock_settings.llm_model_path = ""
            service = ChatService()
            service.llm_service.backend = mock_backend_with_streaming
            yield service


class TestChatServiceStreaming:
    """Tests for ChatService streaming functionality"""

    @pytest.mark.asyncio
    async def test_process_message_stream_basic(self, chat_service_streaming):
        """Test basic streaming message processing"""
        tokens_received = []

        async for chunk in chat_service_streaming.process_message_stream("Hello"):
            if chunk.get("type") == "token":
                tokens_received.append(chunk.get("content", ""))
            elif chunk.get("type") == "session_id":
                assert "session_id" in chunk

        assert len(tokens_received) > 0
        assert "".join(tokens_received) == "Hello there! How can I help?"

    @pytest.mark.asyncio
    async def test_process_message_stream_with_session(self, chat_service_streaming):
        """Test streaming with existing session"""
        session_id = chat_service_streaming._create_session()

        chunks = []
        async for chunk in chat_service_streaming.process_message_stream("Hello", session_id):
            chunks.append(chunk)

        assert len(chunks) > 0
        session_chunks = [c for c in chunks if c.get("type") == "session_id"]
        assert len(session_chunks) > 0
        assert session_chunks[0]["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_process_message_stream_handles_errors(self, chat_service_streaming):
        """Test streaming handles errors gracefully"""

        async def failing_stream(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "Hello", "role": "assistant"}}]}
            raise RuntimeError("Streaming error")

        chat_service_streaming.llm_service.backend.stream_chat_completion = failing_stream

        chunks = []
        async for chunk in chat_service_streaming.process_message_stream("Hello"):
            chunks.append(chunk)

        # Should have received at least one token before error
        token_chunks = [c for c in chunks if c.get("type") == "token"]
        assert len(token_chunks) > 0
