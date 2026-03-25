"""Tests for ToolExecutor"""

from unittest.mock import AsyncMock

import pytest

from zikos.mcp.server import MCPServer
from zikos.mcp.tool import ToolCategory
from zikos.services.llm_orchestration.tool_call_parser import get_tool_call_parser
from zikos.services.llm_orchestration.tool_executor import ToolExecutor


@pytest.fixture
def tool_executor():
    return ToolExecutor()


@pytest.fixture
def mcp_server():
    server = MCPServer()
    server.call_tool = AsyncMock(return_value={"tempo": 120, "bpm": 120.0})
    return server


class TestExecuteToolCall:
    @pytest.mark.asyncio
    async def test_widget_tool_returns_response(self, tool_executor, mcp_server):
        """Widget tools return a tool_call response for the frontend."""
        registry = mcp_server.get_tool_registry()
        parser = get_tool_call_parser()
        tool_call = {
            "id": "call_1",
            "function": {"name": "create_metronome", "arguments": '{"bpm": 120}'},
        }

        result = await tool_executor.execute_tool_call(
            tool_call, registry, mcp_server, "s1", "Let me set up a metronome", parser
        )

        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "create_metronome"
        assert result["tool_id"] == "call_1"
        assert result["arguments"]["bpm"] == 120
        assert "metronome" in result["message"].lower() or result["message"] == ""

    @pytest.mark.asyncio
    async def test_recording_tool_returns_response(self, tool_executor, mcp_server):
        registry = mcp_server.get_tool_registry()
        parser = get_tool_call_parser()
        tool_call = {
            "id": "call_2",
            "function": {
                "name": "request_audio_recording",
                "arguments": '{"prompt": "Play a scale"}',
            },
        }

        result = await tool_executor.execute_tool_call(
            tool_call, registry, mcp_server, "s1", "Please record", parser
        )

        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "request_audio_recording"

    @pytest.mark.asyncio
    async def test_analysis_tool_returns_none(self, tool_executor, mcp_server):
        """Non-widget tools return None — they're executed separately."""
        registry = mcp_server.get_tool_registry()
        parser = get_tool_call_parser()
        tool_call = {
            "id": "call_3",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }

        result = await tool_executor.execute_tool_call(
            tool_call, registry, mcp_server, "s1", "Analyzing...", parser
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_format_returns_none(self, tool_executor, mcp_server):
        registry = mcp_server.get_tool_registry()
        parser = get_tool_call_parser()

        result = await tool_executor.execute_tool_call(
            "not a dict", registry, mcp_server, "s1", "", parser
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_args_still_works(self, tool_executor, mcp_server):
        registry = mcp_server.get_tool_registry()
        parser = get_tool_call_parser()
        tool_call = {
            "id": "call_4",
            "function": {"name": "create_metronome", "arguments": "invalid json{"},
        }

        result = await tool_executor.execute_tool_call(
            tool_call, registry, mcp_server, "s1", "", parser
        )

        assert result is not None
        assert result["arguments"] == {}


class TestExecuteToolAndGetResult:
    @pytest.mark.asyncio
    async def test_success(self, tool_executor, mcp_server):
        registry = mcp_server.get_tool_registry()
        tool_call = {
            "id": "call_1",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, registry, mcp_server, "s1"
        )

        assert result["role"] == "tool"
        assert result["name"] == "analyze_tempo"
        assert result["tool_call_id"] == "call_1"
        assert "120" in result["content"]

    @pytest.mark.asyncio
    async def test_tool_not_found(self, tool_executor, mcp_server):
        registry = mcp_server.get_tool_registry()
        tool_call = {
            "id": "call_1",
            "function": {"name": "nonexistent_tool", "arguments": "{}"},
        }

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, registry, mcp_server, "s1"
        )

        assert result["role"] == "tool"
        assert "not found" in result["content"]

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, tool_executor):
        server = MCPServer()
        server.call_tool = AsyncMock(side_effect=FileNotFoundError("Audio file not found"))
        registry = server.get_tool_registry()
        tool_call = {
            "id": "call_1",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "missing.wav"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(tool_call, registry, server, "s1")

        assert result["role"] == "tool"
        assert "Error" in result["content"]
        assert "not found" in result["content"]

    @pytest.mark.asyncio
    async def test_file_not_found_midi_tool_enhanced_error(self, tool_executor):
        server = MCPServer()
        server.call_tool = AsyncMock(side_effect=FileNotFoundError("MIDI file not found"))
        registry = server.get_tool_registry()
        tool_call = {
            "id": "call_1",
            "function": {"name": "midi_to_audio", "arguments": '{"midi_file_id": "missing"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(tool_call, registry, server, "s1")

        assert "validate_midi" in result["content"]

    @pytest.mark.asyncio
    async def test_generic_error(self, tool_executor):
        server = MCPServer()
        server.call_tool = AsyncMock(side_effect=ValueError("Invalid parameter"))
        registry = server.get_tool_registry()
        tool_call = {
            "id": "call_1",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(tool_call, registry, server, "s1")

        assert "Invalid parameter" in result["content"]

    @pytest.mark.asyncio
    async def test_invalid_format(self, tool_executor, mcp_server):
        registry = mcp_server.get_tool_registry()

        result = await tool_executor.execute_tool_and_get_result(
            "not a dict", registry, mcp_server, "s1"
        )

        assert result["role"] == "tool"
        assert result["name"] == "unknown"


class TestParseToolArgs:
    def test_valid_json(self, tool_executor):
        tool_call = {
            "function": {
                "name": "analyze_tempo",
                "arguments": '{"audio_file_id": "test.wav", "bpm": 120}',
            }
        }

        result = tool_executor._parse_tool_args(tool_call)
        assert result == {"audio_file_id": "test.wav", "bpm": 120}

    def test_dict_format(self, tool_executor):
        tool_call = {
            "function": {"name": "analyze_tempo", "arguments": {"audio_file_id": "test.wav"}}
        }

        result = tool_executor._parse_tool_args(tool_call)
        assert result == {"audio_file_id": "test.wav"}

    def test_invalid_json(self, tool_executor):
        tool_call = {"function": {"name": "analyze_tempo", "arguments": "invalid json{"}}

        assert tool_executor._parse_tool_args(tool_call) == {}

    def test_invalid_format(self, tool_executor):
        assert tool_executor._parse_tool_args("not a dict") == {}

    def test_non_dict_result(self, tool_executor):
        tool_call = {"function": {"name": "x", "arguments": '"just a string"'}}

        assert tool_executor._parse_tool_args(tool_call) == {}


class TestEnhanceFileNotFoundError:
    def test_midi_tool_suggests_validate(self, tool_executor):
        result = tool_executor._enhance_file_not_found_error("midi_to_audio", "MIDI file not found")
        assert "validate_midi" in result

    def test_other_tool_returns_plain_error(self, tool_executor):
        result = tool_executor._enhance_file_not_found_error("analyze_tempo", "File not found")
        assert result == "Error: File not found"
