"""Tests for LLMOrchestrator"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.constants import LLM
from zikos.services.llm_orchestration.orchestrator import IterationState, LLMOrchestrator


class TestIterationState:
    """Tests for IterationState"""

    def test_initialization(self):
        """Test IterationState initialization"""
        state = IterationState()

        assert state.iteration == 0
        assert state.consecutive_tool_calls == 0
        assert state.max_consecutive_tool_calls == LLM.MAX_CONSECUTIVE_TOOL_CALLS
        assert state.recent_tool_calls == []


class TestLLMOrchestrator:
    """Tests for LLMOrchestrator"""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for orchestrator"""
        return {
            "conversation_manager": MagicMock(),
            "message_preparer": MagicMock(),
            "audio_context_enricher": MagicMock(),
            "tool_injector": MagicMock(),
            "tool_call_parser": MagicMock(),
            "tool_executor": MagicMock(),
            "response_validator": MagicMock(),
            "thinking_extractor": MagicMock(),
            "system_prompt_getter": MagicMock(return_value="System prompt"),
        }

    @pytest.fixture
    def orchestrator(self, mock_components):
        """Create LLMOrchestrator instance"""
        return LLMOrchestrator(**mock_components)

    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server"""
        server = MagicMock()
        registry = MagicMock()
        registry.get_all_tools.return_value = []
        registry.get_all_schemas.return_value = []
        server.get_tool_registry.return_value = registry
        return server

    def test_prepare_conversation(self, orchestrator, mock_mcp_server, mock_components):
        """Test preparing conversation"""
        mock_components["conversation_manager"].get_history.return_value = []
        mock_components["audio_context_enricher"].enrich_message.return_value = (
            "enriched message",
            None,
        )

        (
            history,
            original_message,
            tool_registry,
            tools,
            tool_schemas,
            iteration_state,
        ) = orchestrator.prepare_conversation("test message", "session_123", mock_mcp_server)

        assert original_message == "test message"
        assert isinstance(history, list)
        assert tool_registry is not None
        assert isinstance(tools, list)
        assert isinstance(tool_schemas, list)
        assert isinstance(iteration_state, IterationState)

    def test_prepare_iteration_messages(self, orchestrator, mock_components):
        """Test preparing iteration messages"""
        history = [{"role": "user", "content": "test"}]
        mock_components["message_preparer"].prepare.return_value = history
        mock_components["response_validator"].validate_token_limit.return_value = None

        messages, token_error = orchestrator.prepare_iteration_messages(history)

        assert messages == history
        assert token_error is None

    def test_prepare_iteration_messages_token_error(self, orchestrator, mock_components):
        """Test preparing iteration messages with token error"""
        history = [{"role": "user", "content": "test"}]
        mock_components["message_preparer"].prepare.return_value = history
        mock_components["response_validator"].validate_token_limit.return_value = {
            "type": "error",
            "message": "Token limit exceeded",
        }

        messages, token_error = orchestrator.prepare_iteration_messages(history)

        assert messages == history
        assert token_error is not None
        assert token_error["type"] == "error"

    def test_process_llm_response_success(self, orchestrator, mock_components):
        """Test processing LLM response successfully"""
        message_obj = {"content": "Test response", "role": "assistant"}
        history: list[dict[str, Any]] = []
        mock_components["response_validator"].validate_response_content.return_value = None
        mock_components["thinking_extractor"].extract.return_value = ("Test response", "")

        raw_content, cleaned_content, thinking_content = orchestrator.process_llm_response(
            message_obj, history, "session_123"
        )

        assert raw_content == "Test response"
        assert cleaned_content == "Test response"
        assert thinking_content == ""
        assert len(history) == 1

    def test_process_llm_response_with_thinking(self, orchestrator, mock_components):
        """Test processing LLM response with thinking content"""
        message_obj = {"content": "<thinking>I think...</thinking>Response", "role": "assistant"}
        history: list[dict[str, Any]] = []
        mock_components["response_validator"].validate_response_content.return_value = None
        mock_components["thinking_extractor"].extract.return_value = ("Response", "I think...")

        raw_content, cleaned_content, thinking_content = orchestrator.process_llm_response(
            message_obj, history, "session_123"
        )

        assert thinking_content == "I think..."
        assert cleaned_content == "Response"
        assert len(history) == 2
        assert any(msg.get("role") == "thinking" for msg in history)

    def test_process_llm_response_content_error(self, orchestrator, mock_components):
        """Test processing LLM response with content error"""
        message_obj = {"content": "Invalid content", "role": "assistant"}
        history: list[dict[str, Any]] = []
        mock_components["response_validator"].validate_response_content.return_value = {
            "type": "error",
            "message": "Invalid content",
        }

        raw_content, cleaned_content, thinking_content = orchestrator.process_llm_response(
            message_obj, history, "session_123"
        )

        assert raw_content == "Invalid content"
        assert cleaned_content == ""
        assert thinking_content == ""

    @pytest.mark.asyncio
    async def test_process_tool_calls_success(self, orchestrator, mock_components, mock_mcp_server):
        """Test processing tool calls successfully"""
        tool_calls = [
            {
                "id": "call_123",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
            }
        ]
        iteration_state = IterationState()
        history: list[dict[str, Any]] = []
        tool_registry = mock_mcp_server.get_tool_registry()

        mock_components["response_validator"].validate_tool_call_loops.return_value = None
        mock_components["tool_executor"].execute_tool_call = AsyncMock(return_value=None)
        mock_components["tool_executor"].execute_tool_and_get_result = AsyncMock(
            return_value={"role": "tool", "name": "analyze_tempo", "content": "120 BPM"}
        )

        should_continue, widget_response = await orchestrator.process_tool_calls(
            tool_calls, iteration_state, history, tool_registry, mock_mcp_server, "session_123", ""
        )

        assert should_continue is True
        assert widget_response is None
        assert len(history) == 1
        assert iteration_state.consecutive_tool_calls == 1

    @pytest.mark.asyncio
    async def test_process_tool_calls_widget_tool(
        self, orchestrator, mock_components, mock_mcp_server
    ):
        """Test processing tool calls with widget tool"""
        tool_calls = [
            {
                "id": "call_123",
                "function": {"name": "create_metronome", "arguments": '{"bpm": 120}'},
            }
        ]
        iteration_state = IterationState()
        history: list[dict[str, Any]] = []
        tool_registry = mock_mcp_server.get_tool_registry()

        widget_response = {"type": "tool_call", "tool_name": "create_metronome"}
        mock_components["response_validator"].validate_tool_call_loops.return_value = None
        mock_components["tool_executor"].execute_tool_call = AsyncMock(return_value=widget_response)

        should_continue, result = await orchestrator.process_tool_calls(
            tool_calls, iteration_state, history, tool_registry, mock_mcp_server, "session_123", ""
        )

        assert should_continue is False
        assert result == widget_response

    @pytest.mark.asyncio
    async def test_process_tool_calls_loop_detection(
        self, orchestrator, mock_components, mock_mcp_server
    ):
        """Test processing tool calls with loop detection"""
        tool_calls = [
            {
                "id": "call_123",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
            }
        ]
        iteration_state = IterationState()
        iteration_state.consecutive_tool_calls = LLM.MAX_CONSECUTIVE_TOOL_CALLS
        history: list[dict[str, Any]] = []
        tool_registry = mock_mcp_server.get_tool_registry()

        loop_error = {"type": "error", "message": "Tool call loop detected"}
        mock_components["response_validator"].validate_tool_call_loops.return_value = loop_error

        should_continue, result = await orchestrator.process_tool_calls(
            tool_calls, iteration_state, history, tool_registry, mock_mcp_server, "session_123", ""
        )

        assert should_continue is False
        assert result == loop_error

    @pytest.mark.asyncio
    async def test_process_tool_calls_multiple_tools(
        self, orchestrator, mock_components, mock_mcp_server
    ):
        """Test processing multiple tool calls"""
        tool_calls = [
            {
                "id": "call_123",
                "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
            },
            {
                "id": "call_456",
                "function": {"name": "detect_pitch", "arguments": '{"audio_file_id": "test.wav"}'},
            },
        ]
        iteration_state = IterationState()
        history: list[dict[str, Any]] = []
        tool_registry = mock_mcp_server.get_tool_registry()

        mock_components["response_validator"].validate_tool_call_loops.return_value = None
        mock_components["tool_executor"].execute_tool_call = AsyncMock(return_value=None)
        mock_components["tool_executor"].execute_tool_and_get_result = AsyncMock(
            side_effect=[
                {"role": "tool", "name": "analyze_tempo", "content": "120 BPM"},
                {"role": "tool", "name": "detect_pitch", "content": "A4"},
            ]
        )

        should_continue, widget_response = await orchestrator.process_tool_calls(
            tool_calls, iteration_state, history, tool_registry, mock_mcp_server, "session_123", ""
        )

        assert should_continue is True
        assert len(history) == 2
        assert len(iteration_state.recent_tool_calls) == 2

    def test_finalize_response_with_content(self, orchestrator):
        """Test finalizing response with content"""
        iteration_state = IterationState()
        iteration_state.consecutive_tool_calls = 5
        iteration_state.recent_tool_calls = ["tool1", "tool2"]

        result = orchestrator.finalize_response("Test response", "thinking", iteration_state)

        assert result == "Test response"
        assert iteration_state.consecutive_tool_calls == 0
        assert iteration_state.recent_tool_calls == []

    def test_finalize_response_empty_content(self, orchestrator):
        """Test finalizing response with empty content"""
        iteration_state = IterationState()

        result = orchestrator.finalize_response("", "", iteration_state)

        assert "not sure how to help" in result.lower()
        assert iteration_state.consecutive_tool_calls == 0
