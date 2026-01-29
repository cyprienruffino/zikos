"""Unit tests for LLM streaming functionality"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.services.llm import LLMService


@pytest.fixture
def mock_backend_with_streaming():
    """Mock LLM backend with streaming support"""
    backend = MagicMock()
    backend.is_initialized.return_value = True

    # Mock streaming response
    async def stream_chat_completion(*args, **kwargs):
        tokens = ["Hello", " there", "!", " How", " can", " I", " help", "?"]
        for token in tokens:
            yield {
                "choices": [
                    {"delta": {"content": token, "role": "assistant"}, "finish_reason": None}
                ]
            }
        # Final message
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

    backend.stream_chat_completion = stream_chat_completion
    backend.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Test response", "role": "assistant"}}]
    }
    backend.get_cached_system_prompt.return_value = None
    return backend


@pytest.fixture
def llm_service_streaming(mock_backend_with_streaming):
    """Create LLMService instance with mocked streaming backend"""
    mock_backend_with_streaming.get_context_window.return_value = 4096
    with patch("zikos.services.llm.create_backend", return_value=mock_backend_with_streaming):
        with patch("zikos.services.llm.settings") as mock_settings:
            mock_settings.llm_model_path = "/path/to/model.gguf"
            mock_settings.llm_backend = "auto"
            mock_settings.llm_n_ctx = 4096
            mock_settings.llm_n_gpu_layers = 0
            mock_settings.llm_temperature = 0.7
            mock_settings.llm_top_p = 0.9
            mock_settings.llm_top_k = None
            mock_settings.llm_max_thinking_tokens = 0
            service = LLMService()
            yield service


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server"""
    server = MagicMock()
    server.get_tools.return_value = []
    return server


class TestLLMStreaming:
    """Tests for LLM streaming functionality"""

    @pytest.mark.asyncio
    async def test_generate_response_stream_basic(self, llm_service_streaming, mock_mcp_server):
        """Test basic streaming response generation"""
        session_id = "test_session"
        tokens_received = []

        async for chunk in llm_service_streaming.generate_response_stream(
            "Hello", session_id, mock_mcp_server
        ):
            if chunk.get("type") == "token":
                tokens_received.append(chunk.get("content", ""))

        assert len(tokens_received) > 0
        assert "".join(tokens_received) == "Hello there! How can I help?"

    @pytest.mark.asyncio
    async def test_generate_response_stream_without_llm(self, mock_mcp_server):
        """Test streaming when LLM is not available"""
        with patch("zikos.services.llm.create_backend", return_value=None):
            with patch("zikos.services.llm.settings") as mock_settings:
                mock_settings.llm_model_path = ""
                service = LLMService()
                service.backend = None

                chunks = []
                async for chunk in service.generate_response_stream(
                    "Hello", "test_session", mock_mcp_server
                ):
                    chunks.append(chunk)

                assert len(chunks) == 1
                assert chunks[0]["type"] == "error"
                assert "LLM not available" in chunks[0]["message"]

    @pytest.mark.asyncio
    async def test_generate_response_stream_handles_tool_calls(
        self, llm_service_streaming, mock_mcp_server
    ):
        """Test streaming handles tool calls correctly"""
        from zikos.mcp.tool import ToolCategory

        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.RECORDING
        mock_tool_registry = mock_mcp_server.get_tool_registry()
        mock_tool_registry.get_tool.return_value = mock_tool

        # Mock backend to return tool call after streaming
        async def stream_with_tool_call(*args, **kwargs):
            yield {
                "choices": [
                    {"delta": {"content": "Let me", "role": "assistant"}, "finish_reason": None}
                ]
            }
            yield {
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "tool_calls",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "function": {
                                    "name": "request_audio_recording",
                                    "arguments": '{"prompt": "Record audio"}',
                                },
                            }
                        ],
                    }
                ]
            }

        llm_service_streaming.backend.stream_chat_completion = stream_with_tool_call
        mock_mcp_server.call_tool = AsyncMock(return_value={"result": "success"})

        chunks = []
        async for chunk in llm_service_streaming.generate_response_stream(
            "let's record", "test_session", mock_mcp_server
        ):
            chunks.append(chunk)

        # Should have received tokens and then a tool call
        token_chunks = [c for c in chunks if c.get("type") == "token"]
        tool_call_chunks = [c for c in chunks if c.get("type") == "tool_call"]

        assert len(token_chunks) > 0
        assert len(tool_call_chunks) > 0 or any("tool_call" in str(c) for c in chunks)

    @pytest.mark.asyncio
    async def test_generate_response_stream_preserves_conversation_history(
        self, llm_service_streaming, mock_mcp_server
    ):
        """Test that streaming preserves conversation history"""
        session_id = "test_session"

        # First message
        tokens1 = []
        async for chunk in llm_service_streaming.generate_response_stream(
            "Hello", session_id, mock_mcp_server
        ):
            if chunk.get("type") == "token":
                tokens1.append(chunk.get("content", ""))

        # Second message should have context from first
        tokens2 = []
        async for chunk in llm_service_streaming.generate_response_stream(
            "What did I say?", session_id, mock_mcp_server
        ):
            if chunk.get("type") == "token":
                tokens2.append(chunk.get("content", ""))

        # Check that conversation history was maintained
        history = llm_service_streaming._get_conversation_history(session_id)
        assert len(history) > 2  # System + 2 user messages + responses

    @pytest.mark.asyncio
    async def test_generate_response_stream_handles_errors(
        self, llm_service_streaming, mock_mcp_server
    ):
        """Test streaming handles errors gracefully"""

        async def failing_stream(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "Hello", "role": "assistant"}}]}
            raise RuntimeError("Streaming error")

        llm_service_streaming.backend.stream_chat_completion = failing_stream

        chunks = []
        async for chunk in llm_service_streaming.generate_response_stream(
            "Hello", "test_session", mock_mcp_server
        ):
            chunks.append(chunk)

        # Should have received at least one token before error
        token_chunks = [c for c in chunks if c.get("type") == "token"]
        assert len(token_chunks) > 0
