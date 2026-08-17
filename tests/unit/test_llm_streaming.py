"""Tests for LLM streaming functionality"""

from unittest.mock import AsyncMock, patch

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
                with patch("zikos.services.llm_init.settings") as init_s:
                    s.llm_model_path = ""
                    init_s.llm_provider = ""
                    init_s.llm_model_path = ""
                    service = LLMService()

        chunks = []
        async for chunk in service.generate_response_stream("Hello", "s1", mcp_server):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0]["type"] == "error"

    @pytest.mark.asyncio
    async def test_interaction_request_commits_assistant_message(self, mcp_server):
        """Recording widget: assistant message committed immediately, no tool_result yet."""
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

        history = service._get_conversation_history("s1")
        assistant_msgs = [m for m in history if m["role"] == "assistant" and m.get("tool_calls")]
        tool_result_msgs = [m for m in history if m["role"] == "tool"]
        assert (
            len(assistant_msgs) == 1
        ), "assistant message with pending tool_use must be in history"
        assert len(tool_result_msgs) == 0, "no tool_result yet — arrives when recording is done"

    @pytest.mark.asyncio
    async def test_display_widget_commits_assistant_and_synthetic_result(self, mcp_server):
        """Display widget: assistant message + synthetic tool_result committed immediately."""
        service = make_streaming_service(
            response="",
            tool_calls=[
                {
                    "id": "call_met",
                    "function": {
                        "name": "create_metronome",
                        "arguments": '{"bpm": 120}',
                    },
                }
            ],
        )

        chunks = []
        async for chunk in service.generate_response_stream("Show metronome", "s1", mcp_server):
            chunks.append(chunk)

        tool_chunks = [c for c in chunks if c.get("type") == "tool_call"]
        assert len(tool_chunks) > 0

        history = service._get_conversation_history("s1")
        assistant_msgs = [m for m in history if m["role"] == "assistant" and m.get("tool_calls")]
        tool_result_msgs = [m for m in history if m["role"] == "tool"]
        assert len(assistant_msgs) == 1, "assistant message committed"
        assert len(tool_result_msgs) == 1, "synthetic tool_result committed immediately"
        assert "create_metronome" in tool_result_msgs[0]["content"]
        assert assistant_msgs[0]["tool_calls"][0]["id"] == tool_result_msgs[0]["tool_call_id"]

    @pytest.mark.asyncio
    async def test_recording_round_trip_closes_tool_use_pair(self, mcp_server):
        """Full recording flow: tool_use committed when widget shown, tool_result when audio arrives."""
        service = make_streaming_service(
            responses=[
                {
                    "tool_calls": [
                        {
                            "id": "rec_id_1",
                            "function": {
                                "name": "request_audio_recording",
                                "arguments": '{"prompt": "Record yourself"}',
                            },
                        }
                    ]
                },
                "Great recording! Here is my feedback.",
            ]
        )

        # Step 1: LLM requests recording
        async for _ in service.generate_response_stream("Teach me", "s1", mcp_server):
            pass

        history = service._get_conversation_history("s1")
        assert any(m["role"] == "assistant" and m.get("tool_calls") for m in history)
        assert not any(m["role"] == "tool" for m in history), "no tool_result yet"

        # Step 2: user finishes recording → handle_audio_ready closes the pair
        mcp_server.call_tool = AsyncMock(return_value={"bpm": 100})
        with patch.object(
            service.audio_service, "run_baseline_analysis", return_value={"bpm": 100}
        ):
            await service.handle_audio_ready("audio_1.wav", None, "s1", mcp_server)

        history = service._get_conversation_history("s1")
        tool_results = [m for m in history if m["role"] == "tool"]
        assert len(tool_results) == 1, "tool_result injected after recording"

        # The tool_call_id must match the assistant's tool_use id (UUID-reassigned).
        assistant_tool_use = next(
            m for m in history if m["role"] == "assistant" and m.get("tool_calls")
        )
        assert tool_results[0]["tool_call_id"] == assistant_tool_use["tool_calls"][0]["id"]

        # History must be a valid append-only sequence: assistant(tool_use) then tool(result)
        assistant_idx = next(
            i for i, m in enumerate(history) if m["role"] == "assistant" and m.get("tool_calls")
        )
        tool_idx = next(i for i, m in enumerate(history) if m["role"] == "tool")
        assert assistant_idx + 1 == tool_idx, "tool_result immediately follows assistant tool_use"

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
    async def test_tool_call_history_committed_atomically(self, mcp_server):
        """Assistant message and tool results are added to history together after execution."""
        service = make_streaming_service(
            responses=[
                {
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "function": {
                                "name": "analyze_tempo",
                                "arguments": '{"audio_file_id": "test.wav"}',
                            },
                        }
                    ]
                },
                "Here is your tempo analysis.",
            ]
        )

        mcp_server.call_tool = AsyncMock(return_value={"bpm": 120})

        async for _ in service.generate_response_stream("Analyse this", "s1", mcp_server):
            pass

        history = service._get_conversation_history("s1")
        assistant_msgs = [
            (i, m)
            for i, m in enumerate(history)
            if m["role"] == "assistant" and m.get("tool_calls")
        ]
        tool_msgs = [(i, m) for i, m in enumerate(history) if m["role"] == "tool"]

        assert len(assistant_msgs) == 1, "exactly one assistant message with tool_calls"
        assert len(tool_msgs) == 1, "exactly one tool result"
        assert (
            assistant_msgs[0][0] + 1 == tool_msgs[0][0]
        ), "tool result must immediately follow assistant message"

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
