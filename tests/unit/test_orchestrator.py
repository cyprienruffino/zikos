"""Tests for LLMOrchestrator"""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from zikos.constants import LLM
from zikos.mcp.server import MCPServer
from zikos.services.llm_orchestration.audio_context_enricher import AudioContextEnricher
from zikos.services.llm_orchestration.conversation_manager import ConversationManager
from zikos.services.llm_orchestration.message_preparer import MessagePreparer
from zikos.services.llm_orchestration.orchestrator import IterationState, LLMOrchestrator
from zikos.services.llm_orchestration.response_validator import ResponseValidator
from zikos.services.llm_orchestration.thinking_extractor import ThinkingExtractor
from zikos.services.llm_orchestration.tool_call_parser import get_tool_call_parser
from zikos.services.llm_orchestration.tool_executor import ToolExecutor
from zikos.services.llm_orchestration.tool_injector import ToolInjector

SYSTEM_PROMPT = "You are an expert music teacher."


def make_orchestrator():
    return LLMOrchestrator(
        conversation_manager=ConversationManager(lambda: SYSTEM_PROMPT),
        message_preparer=MessagePreparer(),
        audio_context_enricher=AudioContextEnricher(),
        tool_injector=ToolInjector(),
        tool_call_parser=get_tool_call_parser(),
        tool_executor=ToolExecutor(),
        response_validator=ResponseValidator(),
        thinking_extractor=ThinkingExtractor(),
        system_prompt_getter=lambda: SYSTEM_PROMPT,
    )


class TestIterationState:
    def test_initialization(self):
        state = IterationState()

        assert state.iteration == 0
        assert state.max_iterations == LLM.MAX_ITERATIONS
        assert state.consecutive_tool_calls == 0
        assert state.max_consecutive_tool_calls == LLM.MAX_CONSECUTIVE_TOOL_CALLS
        assert state.recent_tool_calls == []


class TestPrepareConversation:
    @pytest.fixture
    def orchestrator(self):
        return make_orchestrator()

    @pytest.fixture
    def mcp_server(self):
        return MCPServer()

    def test_adds_user_message_to_history(self, orchestrator, mcp_server):
        history, original, registry, tools, schemas, state = orchestrator.prepare_conversation(
            "How do I play a C major scale?", "session_1", mcp_server
        )

        assert original == "How do I play a C major scale?"
        user_msgs = [m for m in history if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert "C major scale" in user_msgs[0]["content"]

    def test_initializes_history_with_system_prompt(self, orchestrator, mcp_server):
        history, *_ = orchestrator.prepare_conversation("hello", "new_session", mcp_server)

        system_msgs = [m for m in history if m["role"] == "system"]
        assert len(system_msgs) >= 1
        assert SYSTEM_PROMPT in system_msgs[0]["content"]

    def test_returns_real_tool_registry(self, orchestrator, mcp_server):
        _, _, registry, tools, schemas, _ = orchestrator.prepare_conversation(
            "hello", "s1", mcp_server
        )

        assert len(tools) > 0
        assert len(schemas) > 0
        tool_names = [t.name for t in tools]
        assert "analyze_tempo" in tool_names
        assert "create_metronome" in tool_names

    def test_returns_fresh_iteration_state(self, orchestrator, mcp_server):
        *_, state = orchestrator.prepare_conversation("hello", "s1", mcp_server)

        assert isinstance(state, IterationState)
        assert state.iteration == 0

    def test_enriches_message_with_audio_context(self, orchestrator, mcp_server):
        """When history has audio analysis, message gets enriched."""
        # First call creates the session with system prompt
        history, *_ = orchestrator.prepare_conversation("hello", "session_audio", mcp_server)
        # Add audio analysis to history
        history.append(
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: test.wav\nTempo: 120 BPM",
            }
        )

        # Second call — message should be enriched with audio context
        history2, _, _, _, _, _ = orchestrator.prepare_conversation(
            "What about this recording?", "session_audio", mcp_server
        )
        last_user = [m for m in history2 if m["role"] == "user"][-1]["content"]
        assert "120" in last_user or "Audio Analysis" in last_user


class TestPrepareIterationMessages:
    @pytest.fixture
    def orchestrator(self):
        return make_orchestrator()

    def test_returns_messages_when_within_limit(self, orchestrator):
        history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "hello"},
        ]

        messages, token_error = orchestrator.prepare_iteration_messages(
            history, context_window=4096
        )

        assert token_error is None
        assert len(messages) == 2

    def test_truncates_long_history_to_fit(self, orchestrator):
        """MessagePreparer truncates history before the validator checks,
        so the messages returned should fit within the context window."""
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
        for i in range(200):
            history.append({"role": "user", "content": f"Very long message {'x' * 500} {i}"})

        messages, token_error = orchestrator.prepare_iteration_messages(
            history, context_window=2048
        )

        assert token_error is None
        assert len(messages) < len(history)


class TestProcessLLMResponse:
    @pytest.fixture
    def orchestrator(self):
        return make_orchestrator()

    def test_extracts_clean_content(self, orchestrator):
        msg = {"content": "Here is my feedback on your performance.", "role": "assistant"}
        history: list[dict[str, Any]] = []

        raw, cleaned, thinking = orchestrator.process_llm_response(msg, history, "s1")

        assert cleaned == "Here is my feedback on your performance."
        assert thinking == ""
        assert len(history) == 1

    def test_extracts_thinking_content(self, orchestrator):
        msg = {
            "content": "<thinking>Let me analyze this...</thinking>Great job on the tempo!",
            "role": "assistant",
        }
        history: list[dict[str, Any]] = []

        raw, cleaned, thinking = orchestrator.process_llm_response(msg, history, "s1")

        assert "Great job" in cleaned
        assert "analyze this" in thinking
        assert any(m["role"] == "thinking" for m in history)

    def test_detects_gibberish(self, orchestrator):
        gibberish = " ".join(["x"] * 600)
        msg = {"content": gibberish, "role": "assistant"}
        history: list[dict[str, Any]] = []

        _, cleaned, _ = orchestrator.process_llm_response(msg, history, "s1")

        assert cleaned == ""


class TestProcessToolCalls:
    @pytest.fixture
    def orchestrator(self):
        return make_orchestrator()

    @pytest.fixture
    def mcp_server(self):
        server = MCPServer()
        server.call_tool = AsyncMock(return_value={"tempo": 120, "stability": 0.95, "bpm": 120})
        return server

    @pytest.mark.asyncio
    async def test_executes_tool_and_adds_result_to_history(self, orchestrator, mcp_server):
        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
            }
        ]
        state = IterationState()
        history: list[dict[str, Any]] = []
        registry = mcp_server.get_tool_registry()

        should_continue, result, infos = await orchestrator.process_tool_calls(
            tool_calls, state, history, registry, mcp_server, "s1", ""
        )

        assert should_continue is True
        assert result is None
        assert len(history) == 1
        assert history[0]["role"] == "tool"
        assert "120" in history[0]["content"]
        assert state.consecutive_tool_calls == 1

    @pytest.mark.asyncio
    async def test_returns_tool_call_infos_for_ui(self, orchestrator, mcp_server):
        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "f1"}'},
            },
            {
                "id": "call_2",
                "function": {"name": "detect_pitch", "arguments": '{"audio_file_id": "f1"}'},
            },
        ]
        state = IterationState()
        registry = mcp_server.get_tool_registry()

        _, _, infos = await orchestrator.process_tool_calls(
            tool_calls, state, [], registry, mcp_server, "s1", ""
        )

        assert len(infos) == 2
        assert infos[0]["tool_name"] == "analyze_tempo"
        assert infos[1]["tool_name"] == "detect_pitch"

    @pytest.mark.asyncio
    async def test_widget_tool_returns_without_executing(self, orchestrator):
        """Widget tools are returned to the frontend, not executed via MCP."""
        server = MCPServer()
        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "create_metronome", "arguments": '{"bpm": 120}'},
            }
        ]
        state = IterationState()
        registry = server.get_tool_registry()

        should_continue, result, infos = await orchestrator.process_tool_calls(
            tool_calls, state, [], registry, server, "s1", "Here's a metronome"
        )

        assert should_continue is False
        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "create_metronome"
        assert result["arguments"]["bpm"] == 120

    @pytest.mark.asyncio
    async def test_loop_detection_triggers(self, orchestrator, mcp_server):
        state = IterationState()
        state.consecutive_tool_calls = LLM.MAX_CONSECUTIVE_TOOL_CALLS
        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "analyze_tempo", "arguments": "{}"},
            }
        ]
        registry = mcp_server.get_tool_registry()

        should_continue, result, _ = await orchestrator.process_tool_calls(
            tool_calls, state, [], registry, mcp_server, "s1", ""
        )

        assert should_continue is False
        assert result is not None
        assert "error_type" in result
        assert "too_many" in result["error_type"]

    @pytest.mark.asyncio
    async def test_tracks_recent_tool_calls(self, orchestrator, mcp_server):
        state = IterationState()
        registry = mcp_server.get_tool_registry()
        tool_calls = [
            {"id": "c1", "function": {"name": "analyze_tempo", "arguments": "{}"}},
            {"id": "c2", "function": {"name": "detect_pitch", "arguments": "{}"}},
        ]

        await orchestrator.process_tool_calls(tool_calls, state, [], registry, mcp_server, "s1", "")

        assert state.recent_tool_calls == ["analyze_tempo", "detect_pitch"]


class TestFinalizeResponse:
    def test_resets_state(self):
        orchestrator = make_orchestrator()
        state = IterationState()
        state.consecutive_tool_calls = 5
        state.recent_tool_calls = ["t1", "t2"]

        result = orchestrator.finalize_response("Good work!", "thinking", state)

        assert result == "Good work!"
        assert state.consecutive_tool_calls == 0
        assert state.recent_tool_calls == []

    def test_fallback_on_empty_content(self):
        orchestrator = make_orchestrator()
        state = IterationState()

        result = orchestrator.finalize_response("", "", state)

        assert "not sure how to help" in result.lower()
