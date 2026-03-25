"""Tests for StreamProcessor"""

from typing import Any

import pytest

from zikos.services.llm_orchestration.stream_processor import StreamProcessor, StreamResult


async def make_stream(chunks: list[dict[str, Any]]):
    """Create an async iterator from a list of chunks."""
    for chunk in chunks:
        yield chunk


def make_chunk(content: str | None = None, finish_reason: str | None = None, tool_calls=None):
    """Build a chunk in the format stream_chat_completion returns."""
    delta: dict[str, Any] = {}
    choice: dict[str, Any] = {"delta": delta}
    if content is not None:
        delta["content"] = content
    if tool_calls is not None:
        delta["tool_calls"] = tool_calls
    if finish_reason is not None:
        choice["finish_reason"] = finish_reason
    return {"choices": [choice]}


class TestStreamProcessor:
    @pytest.fixture
    def processor(self):
        return StreamProcessor()

    @pytest.mark.asyncio
    async def test_basic_token_streaming(self, processor):
        stream = make_stream(
            [
                make_chunk("Hello"),
                make_chunk(" world"),
                make_chunk(finish_reason="stop"),
            ]
        )
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result):
            tokens.append(chunk)

        assert len(tokens) == 2
        assert tokens[0] == {"type": "token", "content": "Hello"}
        assert tokens[1] == {"type": "token", "content": " world"}
        assert result.accumulated_content == "Hello world"
        assert result.tool_calls is None
        assert result.thinking_budget_exceeded is False

    @pytest.mark.asyncio
    async def test_tool_call_accumulation(self, processor):
        tool_call = {"id": "1", "function": {"name": "analyze_tempo", "arguments": "{}"}}
        stream = make_stream(
            [
                make_chunk("text"),
                make_chunk(tool_calls=[tool_call]),
                make_chunk(finish_reason="tool_calls"),
            ]
        )
        result = StreamResult()
        async for _ in processor.process(stream, result):
            pass

        assert result.tool_calls == [tool_call]

    @pytest.mark.asyncio
    async def test_thinking_suppressed_within_budget(self, processor):
        stream = make_stream(
            [
                make_chunk("<think>"),
                make_chunk("reasoning"),
                make_chunk("</think>"),
                make_chunk("visible"),
                make_chunk(finish_reason="stop"),
            ]
        )
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result, max_thinking=100):
            tokens.append(chunk)

        assert len(tokens) == 1
        assert tokens[0]["content"] == "visible"
        assert result.thinking_budget_exceeded is False

    @pytest.mark.asyncio
    async def test_thinking_budget_exceeded(self, processor):
        stream = make_stream(
            [
                make_chunk("<think>"),
                make_chunk("tok1"),
                make_chunk("tok2"),
                make_chunk("tok3"),
                make_chunk("should not reach"),
            ]
        )
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result, max_thinking=3):
            tokens.append(chunk)

        assert tokens == []
        assert result.thinking_budget_exceeded is True
        assert "tok1" in result.accumulated_content

    @pytest.mark.asyncio
    async def test_nothink_retry_strips_tags(self, processor):
        stream = make_stream(
            [
                make_chunk("<think>"),
                make_chunk("reasoning"),
                make_chunk("</think>"),
                make_chunk("visible"),
                make_chunk(finish_reason="stop"),
            ]
        )
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result, nothink_retry=True):
            tokens.append(chunk)

        visible = "".join(t["content"] for t in tokens)
        assert "<think>" not in visible
        assert "</think>" not in visible
        assert "reasoning" in visible
        assert "visible" in visible

    @pytest.mark.asyncio
    async def test_non_string_token_skipped(self, processor):
        chunks = [
            {"choices": [{"delta": {"content": 42}}]},
            make_chunk("valid"),
            make_chunk(finish_reason="stop"),
        ]
        stream = make_stream(chunks)
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result):
            tokens.append(chunk)

        assert len(tokens) == 1
        assert tokens[0]["content"] == "valid"

    @pytest.mark.asyncio
    async def test_empty_stream(self, processor):
        stream = make_stream([])
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result):
            tokens.append(chunk)

        assert tokens == []
        assert result.accumulated_content == ""
        assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_tool_calls_in_final_choice(self, processor):
        """Tool calls can appear in the final choice rather than in delta."""
        tool_call = {"id": "1", "function": {"name": "detect_pitch", "arguments": "{}"}}
        chunks = [
            make_chunk("text"),
            {"choices": [{"delta": {}, "finish_reason": "tool_calls", "tool_calls": [tool_call]}]},
        ]
        stream = make_stream(chunks)
        result = StreamResult()
        async for _ in processor.process(stream, result):
            pass

        assert result.tool_calls == [tool_call]

    @pytest.mark.asyncio
    async def test_unlimited_thinking_passes_through(self, processor):
        """With max_thinking=0 (unlimited), thinking tokens are suppressed but no budget check."""
        stream = make_stream(
            [
                make_chunk("Hello"),
                make_chunk(finish_reason="stop"),
            ]
        )
        result = StreamResult()
        tokens = []
        async for chunk in processor.process(stream, result, max_thinking=0):
            tokens.append(chunk)

        assert len(tokens) == 1
        assert result.thinking_budget_exceeded is False
