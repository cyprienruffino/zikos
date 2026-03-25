"""Tests for ChatService streaming"""

from unittest.mock import patch

import pytest

from tests.helpers.fake_backend import FakeBackend
from zikos.services.chat import ChatService


def make_chat_service(response: str = "Hello there! How can I help?"):
    backend = FakeBackend(response)
    backend.initialize(model_path="fake.gguf", n_ctx=4096)

    with patch("zikos.services.llm_init.create_backend", return_value=backend):
        with patch("zikos.services.llm.settings") as s:
            s.llm_model_path = ""
            service = ChatService()
            service.llm_service.backend = backend
            return service


class TestChatServiceStreaming:
    @pytest.mark.asyncio
    async def test_streams_tokens(self):
        service = make_chat_service("Hello there! How can I help?")
        tokens = []

        async for chunk in service.process_message_stream("Hello"):
            if chunk.get("type") == "token":
                tokens.append(chunk["content"])

        full = "".join(tokens)
        assert "Hello" in full
        assert "help" in full

    @pytest.mark.asyncio
    async def test_yields_session_id(self):
        service = make_chat_service("OK")

        chunks = []
        async for chunk in service.process_message_stream("Hello"):
            chunks.append(chunk)

        session_chunks = [c for c in chunks if c.get("type") == "session_id"]
        assert len(session_chunks) == 1
        assert "session_id" in session_chunks[0]

    @pytest.mark.asyncio
    async def test_preserves_session(self):
        service = make_chat_service("Reply")
        session_id = service._create_session()

        chunks = []
        async for chunk in service.process_message_stream("Hello", session_id):
            chunks.append(chunk)

        session_chunks = [c for c in chunks if c.get("type") == "session_id"]
        assert session_chunks[0]["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_handles_streaming_error(self):
        service = make_chat_service("OK")

        async def failing_stream(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "partial"}, "finish_reason": None}]}
            raise RuntimeError("Stream died")

        service.llm_service.backend.stream_chat_completion = failing_stream  # type: ignore[assignment]

        chunks = []
        async for chunk in service.process_message_stream("Hello"):
            chunks.append(chunk)

        token_chunks = [c for c in chunks if c.get("type") == "token"]
        assert len(token_chunks) > 0
