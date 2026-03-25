"""Tests for LLM streaming functionality"""

from unittest.mock import patch

import pytest

from tests.helpers.fake_backend import FakeBackend
from zikos.mcp.server import MCPServer
from zikos.services.llm import LLMService


def make_streaming_service(response: str = "Hello there! How can I help?", **kwargs):
    backend = FakeBackend(response, **kwargs)
    backend.initialize(model_path="fake.gguf", n_ctx=4096)

    with patch("zikos.services.llm_init.create_backend", return_value=backend):
        with patch("zikos.services.llm.settings") as s:
            s.llm_model_path = ""
            service = LLMService()
            service.backend = backend
            return service


@pytest.fixture
def mcp_server():
    return MCPServer()


class TestLLMStreaming:
    @pytest.mark.asyncio
    async def test_streams_tokens(self, mcp_server):
        service = make_streaming_service("Hello there! How can I help?")
        tokens = []

        async for chunk in service.generate_response_stream("Hi", "s1", mcp_server):
            if chunk.get("type") == "token":
                tokens.append(chunk["content"])

        full_text = "".join(tokens)
        assert "Hello" in full_text
        assert "help" in full_text

    @pytest.mark.asyncio
    async def test_yields_final_response(self, mcp_server):
        service = make_streaming_service("Good job on the tempo!")
        chunks = []

        async for chunk in service.generate_response_stream("How did I do?", "s1", mcp_server):
            chunks.append(chunk)

        response_chunks = [c for c in chunks if c.get("type") == "response"]
        assert len(response_chunks) == 1
        assert "tempo" in response_chunks[0]["message"].lower()

    @pytest.mark.asyncio
    async def test_error_without_backend(self, mcp_server):
        with patch("zikos.services.llm_init.create_backend", return_value=None):
            with patch("zikos.services.llm.settings") as s:
                s.llm_model_path = ""
                service = LLMService()

        chunks = []
        async for chunk in service.generate_response_stream("Hello", "s1", mcp_server):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "error"

    @pytest.mark.asyncio
    async def test_tool_call_streaming(self, mcp_server):
        service = make_streaming_service(
            response="",
            tool_calls=[
                {
                    "id": "call_1",
                    "function": {
                        "name": "request_audio_recording",
                        "arguments": '{"prompt": "Record"}',
                    },
                }
            ],
        )

        chunks = []
        async for chunk in service.generate_response_stream("Let's record", "s1", mcp_server):
            chunks.append(chunk)

        tool_chunks = [c for c in chunks if c.get("type") == "tool_call"]
        assert len(tool_chunks) > 0

    @pytest.mark.asyncio
    async def test_preserves_conversation_history(self, mcp_server):
        service = make_streaming_service("First reply")

        async for _ in service.generate_response_stream("Hello", "s1", mcp_server):
            pass
        async for _ in service.generate_response_stream("Follow-up", "s1", mcp_server):
            pass

        history = service._get_conversation_history("s1")
        user_msgs = [m for m in history if m["role"] == "user"]
        assert len(user_msgs) == 2

    @pytest.mark.asyncio
    async def test_handles_streaming_error(self, mcp_server):
        service = make_streaming_service("OK")

        async def failing_stream(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "partial"}, "finish_reason": None}]}
            raise RuntimeError("Stream died")

        service.backend.stream_chat_completion = failing_stream  # type: ignore[assignment]

        chunks = []
        async for chunk in service.generate_response_stream("Hello", "s1", mcp_server):
            chunks.append(chunk)

        token_chunks = [c for c in chunks if c.get("type") == "token"]
        assert len(token_chunks) > 0
