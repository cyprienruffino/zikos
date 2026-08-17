"""Tests for LLMOrchestrator"""

from unittest.mock import AsyncMock

import pytest

from zikos.constants import LLM
from zikos.mcp.server import MCPServer
from zikos.services.llm_orchestration.conversation_manager import ConversationManager
from zikos.services.llm_orchestration.message_preparer import MessagePreparer
from zikos.services.llm_orchestration.orchestrator import IterationState, LLMOrchestrator
from zikos.services.llm_orchestration.response_validator import ResponseValidator
from zikos.services.llm_orchestration.tool_call_parser import get_tool_call_parser
from zikos.services.llm_orchestration.tool_executor import ToolExecutor
from zikos.services.llm_orchestration.tool_injector import ToolInjector

SYSTEM_PROMPT = "You are an expert music teacher."


def make_orchestrator():
    return LLMOrchestrator(
        conversation_manager=ConversationManager(lambda: SYSTEM_PROMPT),
        message_preparer=MessagePreparer(),
        tool_injector=ToolInjector(),
        tool_call_parser=get_tool_call_parser(),
        tool_executor=ToolExecutor(),
        response_validator=ResponseValidator(),
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

    def test_empty_message_becomes_session_start_sentinel(self, orchestrator, mcp_server):
        """An empty greeting message must never produce content:'' (rejected by
        Anthropic) — it becomes the '[session start]' sentinel."""
        history, *_ = orchestrator.prepare_conversation("", "session_greet", mcp_server)

        user_msgs = [m for m in history if m["role"] == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0]["content"] == "[session start]"

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
    async def test_executes_tool_and_returns_results(self, orchestrator, mcp_server):
        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
            }
        ]
        state = IterationState()
        registry = mcp_server.get_tool_registry()

        should_continue, result, infos, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, mcp_server, "s1", ""
        )

        assert should_continue is True
        assert result is None
        assert len(tool_results) == 1
        assert tool_results[0]["role"] == "tool"
        assert "120" in tool_results[0]["content"]
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

        _, _, infos, _ = await orchestrator.process_tool_calls(
            tool_calls, state, registry, mcp_server, "s1", ""
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

        should_continue, result, infos, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, server, "s1", "Here's a metronome"
        )

        assert should_continue is False
        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "create_metronome"
        assert result["arguments"]["bpm"] == 120
        assert tool_results == []

    @pytest.mark.asyncio
    async def test_mixed_analysis_and_widget_keeps_executed_results(self, orchestrator, mcp_server):
        """A batch of [analysis_call, widget_call] must return the widget response
        AND the executed analysis results so the caller can commit them."""
        tool_calls = [
            {
                "id": "call_analysis",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "f1"}'},
            },
            {
                "id": "call_widget",
                "function": {"name": "create_metronome", "arguments": '{"bpm": 100}'},
            },
        ]
        state = IterationState()
        registry = mcp_server.get_tool_registry()

        should_continue, result, infos, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, mcp_server, "s1", ""
        )

        assert should_continue is False
        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "create_metronome"
        assert len(tool_results) == 1
        assert tool_results[0]["role"] == "tool"
        assert tool_results[0]["tool_call_id"] == "call_analysis"
        assert "120" in tool_results[0]["content"]

    @pytest.mark.asyncio
    async def test_multiple_widgets_extra_calls_get_synthetic_results(self, orchestrator):
        """Only the first widget is returned; extra widget calls are closed with
        synthetic tool results so nothing dangles."""
        server = MCPServer()
        tool_calls = [
            {"id": "w1", "function": {"name": "create_metronome", "arguments": '{"bpm": 90}'}},
            {"id": "w2", "function": {"name": "create_metronome", "arguments": '{"bpm": 120}'}},
        ]
        state = IterationState()
        registry = server.get_tool_registry()

        should_continue, result, _, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, server, "s1", ""
        )

        assert should_continue is False
        assert result["arguments"]["bpm"] == 90
        assert len(tool_results) == 1
        assert tool_results[0]["tool_call_id"] == "w2"
        assert "Skipped" in tool_results[0]["content"]

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

        should_continue, result, _, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, mcp_server, "s1", ""
        )

        assert should_continue is False
        assert result is not None
        assert "error_type" in result
        assert "too_many" in result["error_type"]
        assert tool_results == []

    @pytest.mark.asyncio
    async def test_tracks_recent_tool_calls(self, orchestrator, mcp_server):
        state = IterationState()
        registry = mcp_server.get_tool_registry()
        tool_calls = [
            {"id": "c1", "function": {"name": "analyze_tempo", "arguments": "{}"}},
            {"id": "c2", "function": {"name": "detect_pitch", "arguments": "{}"}},
        ]

        await orchestrator.process_tool_calls(tool_calls, state, registry, mcp_server, "s1", "")

        assert state.recent_tool_calls == [
            "analyze_tempo({})",
            "detect_pitch({})",
        ]

    @pytest.mark.asyncio
    async def test_loop_detected_within_single_batch(self, orchestrator, mcp_server):
        """The identical call repeated within ONE response must trip the loop
        detector before execution."""
        tool_calls = [
            {
                "id": f"c{i}",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "a.wav"}'},
            }
            for i in range(LLM.REPETITIVE_PATTERN_THRESHOLD)
        ]
        state = IterationState()
        registry = mcp_server.get_tool_registry()

        should_continue, result, _, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, mcp_server, "s1", ""
        )

        assert should_continue is False
        assert result is not None and result["error_type"] == "repetitive_tool_calls"
        assert tool_results == []
        mcp_server.call_tool.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_same_tool_different_args_is_not_a_loop(self, orchestrator, mcp_server):
        """Repeating a tool with DIFFERENT arguments (e.g. different segments)
        is legitimate — the loop signature includes canonical args."""
        tool_calls = [
            {
                "id": f"c{i}",
                "function": {
                    "name": "analyze_tempo",
                    "arguments": f'{{"audio_file_id": "seg_{i}.wav"}}',
                },
            }
            for i in range(LLM.REPETITIVE_PATTERN_THRESHOLD)
        ]
        state = IterationState()
        registry = mcp_server.get_tool_registry()

        should_continue, result, _, tool_results = await orchestrator.process_tool_calls(
            tool_calls, state, registry, mcp_server, "s1", ""
        )

        assert should_continue is True
        assert result is None
        assert len(tool_results) == LLM.REPETITIVE_PATTERN_THRESHOLD
