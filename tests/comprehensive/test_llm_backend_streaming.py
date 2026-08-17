"""Unit tests for LLM backend streaming functionality

Note: This file imports excluded backend implementations (llama_cpp, transformers).
These are only tested in comprehensive tests that require real models.
For unit tests, we test the base interface only.
"""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest

from zikos.services.llm_backends.base import LLMBackend
from zikos.services.llm_backends.llama_cpp import LlamaCppBackend
from zikos.services.llm_backends.transformers import TransformersBackend

pytestmark = pytest.mark.comprehensive


class MockBackend(LLMBackend):
    """Mock backend for testing base streaming implementation"""

    def initialize(self, model_path: str, n_ctx: int = 32768, **kwargs):
        pass

    def create_chat_completion(self, messages, tools=None, **kwargs):
        return {"choices": [{"message": {"content": "Test response", "role": "assistant"}}]}

    def supports_tools(self) -> bool:
        return False

    def supports_system_messages(self) -> bool:
        return True

    def get_context_window(self) -> int:
        return 4096

    def close(self) -> None:
        pass

    def is_initialized(self) -> bool:
        return True


class TestBaseBackendStreaming:
    """Tests for base backend streaming fallback implementation"""

    @pytest.mark.asyncio
    async def test_stream_chat_completion_fallback(self):
        """Test that base backend fallback streaming works"""
        backend = MockBackend()

        tokens = []
        async for chunk in backend.stream_chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        ):
            if chunk.get("choices", [{}])[0].get("delta", {}).get("content"):
                tokens.append(chunk["choices"][0]["delta"]["content"])

        assert len(tokens) > 0
        assert "".join(tokens) == "Test response"

    @pytest.mark.asyncio
    async def test_stream_fallback_preserves_formatting(self):
        """The fallback must not re-split content on whitespace: newlines and
        indentation (e.g. MIDI text) must survive verbatim."""
        backend = MockBackend()
        midi_text = "MFile 1 1 480\nMTrk\n  0 Meta SeqName \"test\"\nTrkEnd"
        backend.create_chat_completion = MagicMock(  # type: ignore[method-assign]
            return_value={"choices": [{"message": {"content": midi_text, "role": "assistant"}}]}
        )

        tokens = []
        async for chunk in backend.stream_chat_completion(
            messages=[{"role": "user", "content": "MIDI please"}]
        ):
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                tokens.append(delta["content"])

        assert "".join(tokens) == midi_text

    @pytest.mark.asyncio
    async def test_stream_fallback_includes_tool_calls(self):
        """Native tool_calls from the message must appear in the final chunk's delta."""
        backend = MockBackend()
        tool_calls = [
            {"id": "c1", "function": {"name": "analyze_tempo", "arguments": "{}"}},
        ]
        backend.create_chat_completion = MagicMock(  # type: ignore[method-assign]
            return_value={
                "choices": [
                    {
                        "message": {"content": "", "role": "assistant", "tool_calls": tool_calls},
                        "finish_reason": "tool_calls",
                    }
                ]
            }
        )

        chunks = []
        async for chunk in backend.stream_chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        ):
            chunks.append(chunk)

        final = chunks[-1]["choices"][0]
        assert final["finish_reason"] == "tool_calls"
        assert final["delta"]["tool_calls"] == tool_calls

    @pytest.mark.asyncio
    async def test_stream_chat_completion_with_empty_response(self):
        """Test streaming with empty response"""
        backend = MockBackend()
        backend.create_chat_completion = MagicMock(  # type: ignore[method-assign]
            return_value={"choices": [{"message": {"content": "", "role": "assistant"}}]}
        )

        chunks = []
        async for chunk in backend.stream_chat_completion(
            messages=[{"role": "user", "content": "Hello"}]
        ):
            chunks.append(chunk)

        # Should still yield final chunk with finish_reason
        assert len(chunks) > 0
        final_chunk = chunks[-1]
        assert final_chunk.get("choices", [{}])[0].get("finish_reason") == "stop"

    @pytest.mark.asyncio
    async def test_stream_chat_completion_passes_parameters(self):
        """Test that streaming passes parameters to create_chat_completion"""
        backend = MockBackend()
        backend.create_chat_completion = MagicMock(  # type: ignore[method-assign]
            return_value={"choices": [{"message": {"content": "Test", "role": "assistant"}}]}
        )

        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"type": "function", "function": {"name": "test_tool"}}]

        async for _ in backend.stream_chat_completion(
            messages=messages, tools=tools, temperature=0.8, top_p=0.9
        ):
            pass

        backend.create_chat_completion.assert_called_once()
        call_kwargs = backend.create_chat_completion.call_args.kwargs
        assert call_kwargs["messages"] == messages
        assert call_kwargs["tools"] == tools
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["top_p"] == 0.9


class TestLlamaCppBackendStreaming:
    """Tests for LlamaCpp backend streaming"""

    def test_stream_chat_completion_not_initialized(self):
        """Test streaming fails when backend not initialized"""
        backend = LlamaCppBackend()

        async def test():
            async for _ in backend.stream_chat_completion(
                messages=[{"role": "user", "content": "Hello"}]
            ):
                pass

        with pytest.raises(RuntimeError, match="Backend not initialized"):
            import asyncio

            asyncio.run(test())

    @pytest.mark.asyncio
    async def test_stream_chat_completion_with_mock_llm(self):
        """Test streaming with mocked llama-cpp-python"""
        backend = LlamaCppBackend()
        backend.llm = MagicMock()

        mock_stream = [
            {"choices": [{"delta": {"content": "Hello", "role": "assistant"}}]},
            {"choices": [{"delta": {"content": " there", "role": "assistant"}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]
        backend.llm.create_chat_completion.return_value = iter(mock_stream)
        backend.n_ctx = 4096

        tokens = []
        async for chunk in backend.stream_chat_completion(
            messages=[{"role": "user", "content": "Hello"}], temperature=0.7
        ):
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                tokens.append(delta["content"])

        assert "".join(tokens) == "Hello there"
        backend.llm.create_chat_completion.assert_called_once()
        call_kwargs = backend.llm.create_chat_completion.call_args.kwargs
        assert call_kwargs["stream"] is True
        assert call_kwargs["temperature"] == 0.7


class TestTransformersBackendStreaming:
    """Tests for Transformers backend streaming"""

    def test_stream_chat_completion_not_initialized(self):
        """Test streaming fails when backend not initialized"""
        backend = TransformersBackend()

        async def test():
            async for _ in backend.stream_chat_completion(
                messages=[{"role": "user", "content": "Hello"}]
            ):
                pass

        with pytest.raises(RuntimeError, match="Backend not initialized"):
            import asyncio

            asyncio.run(test())

    @pytest.mark.asyncio
    async def test_stream_chat_completion_fallback_when_streamer_unavailable(self):
        """Test streaming falls back to base implementation when TextIteratorStreamer unavailable"""
        backend = TransformersBackend()
        backend.model = MagicMock()
        backend.tokenizer = MagicMock()
        backend.device = "cpu"
        backend.n_ctx = 4096

        # Mock TextIteratorStreamer as None to trigger fallback
        with patch("zikos.services.llm_backends.transformers.TextIteratorStreamer", None):
            with patch.object(
                backend,
                "create_chat_completion",
                return_value={"choices": [{"message": {"content": "Test", "role": "assistant"}}]},
            ) as mock_create:
                tokens = []
                async for chunk in backend.stream_chat_completion(
                    messages=[{"role": "user", "content": "Hello"}]
                ):
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        tokens.append(delta["content"])

                # Should have used fallback (base implementation)
                assert len(tokens) > 0
                mock_create.assert_called_once()
