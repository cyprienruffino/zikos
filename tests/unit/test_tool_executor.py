"""Tests for ToolExecutor"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.mcp.tool import ToolCategory
from zikos.services.llm_orchestration.tool_executor import ToolExecutor


class TestToolExecutor:
    """Tests for ToolExecutor"""

    @pytest.fixture
    def tool_executor(self):
        """Create ToolExecutor instance"""
        return ToolExecutor()

    @pytest.fixture
    def mock_tool_registry(self):
        """Create mock tool registry"""
        registry = MagicMock()
        return registry

    @pytest.fixture
    def mock_mcp_server(self):
        """Create mock MCP server"""
        server = MagicMock()
        server.call_tool = AsyncMock()
        return server

    @pytest.mark.asyncio
    async def test_execute_tool_call_widget_tool(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing widget tool call"""
        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.WIDGET
        mock_tool_registry.get_tool.return_value = mock_tool

        tool_call = {
            "id": "call_123",
            "function": {"name": "create_metronome", "arguments": '{"bpm": 120}'},
        }

        mock_parser = MagicMock()
        mock_parser.strip_tool_call_tags.return_value = "Cleaned message"

        result = await tool_executor.execute_tool_call(
            tool_call,
            mock_tool_registry,
            mock_mcp_server,
            "session_123",
            "User message",
            mock_parser,
        )

        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "create_metronome"
        assert result["tool_id"] == "call_123"

    @pytest.mark.asyncio
    async def test_execute_tool_call_recording_tool(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing recording tool call"""
        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.RECORDING
        mock_tool_registry.get_tool.return_value = mock_tool

        tool_call = {
            "id": "call_456",
            "function": {"name": "request_audio_recording", "arguments": '{"duration": 5}'},
        }

        mock_parser = MagicMock()
        mock_parser.strip_tool_call_tags.return_value = ""

        result = await tool_executor.execute_tool_call(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123", "", mock_parser
        )

        assert result is not None
        assert result["type"] == "tool_call"
        assert result["tool_name"] == "request_audio_recording"

    @pytest.mark.asyncio
    async def test_execute_tool_call_regular_tool(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing regular (non-widget) tool call"""
        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.AUDIO_ANALYSIS
        mock_tool_registry.get_tool.return_value = mock_tool

        tool_call = {
            "id": "call_789",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }

        mock_parser = MagicMock()

        result = await tool_executor.execute_tool_call(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123", "Message", mock_parser
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_execute_tool_call_invalid_format(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool call with invalid format"""
        tool_call = "not a dict"

        mock_parser = MagicMock()

        result = await tool_executor.execute_tool_call(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123", "Message", mock_parser
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_execute_tool_call_invalid_json_args(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool call with invalid JSON arguments"""
        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.WIDGET
        mock_tool_registry.get_tool.return_value = mock_tool

        tool_call = {
            "id": "call_123",
            "function": {"name": "create_metronome", "arguments": "invalid json{"},
        }

        mock_parser = MagicMock()
        mock_parser.strip_tool_call_tags.return_value = ""

        result = await tool_executor.execute_tool_call(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123", "", mock_parser
        )

        assert result is not None
        assert result["arguments"] == {}

    @pytest.mark.asyncio
    async def test_execute_tool_and_get_result_success(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool and getting result successfully"""
        mock_tool = MagicMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        mock_mcp_server.call_tool.return_value = {"tempo": 120, "bpm": 120}

        tool_call = {
            "id": "call_123",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123"
        )

        assert result["role"] == "tool"
        assert result["name"] == "analyze_tempo"
        assert result["tool_call_id"] == "call_123"
        assert "120" in result["content"]

    @pytest.mark.asyncio
    async def test_execute_tool_and_get_result_tool_not_found(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool that doesn't exist"""
        mock_tool_registry.get_tool.return_value = None

        tool_call = {
            "id": "call_123",
            "function": {"name": "unknown_tool", "arguments": "{}"},
        }

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123"
        )

        assert result["role"] == "tool"
        assert result["name"] == "unknown_tool"
        assert "not found" in result["content"]

    @pytest.mark.asyncio
    async def test_execute_tool_and_get_result_file_not_found(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool that raises FileNotFoundError"""
        mock_tool = MagicMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        mock_mcp_server.call_tool.side_effect = FileNotFoundError("Audio file not found")

        tool_call = {
            "id": "call_123",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "missing.wav"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123"
        )

        assert result["role"] == "tool"
        assert "Error" in result["content"]
        assert "not found" in result["content"]

    @pytest.mark.asyncio
    async def test_execute_tool_and_get_result_generic_error(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool that raises generic exception"""
        mock_tool = MagicMock()
        mock_tool_registry.get_tool.return_value = mock_tool
        mock_mcp_server.call_tool.side_effect = ValueError("Invalid parameter")

        tool_call = {
            "id": "call_123",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123"
        )

        assert result["role"] == "tool"
        assert "Error" in result["content"]
        assert "Invalid parameter" in result["content"]

    @pytest.mark.asyncio
    async def test_execute_tool_and_get_result_invalid_format(
        self, tool_executor, mock_tool_registry, mock_mcp_server
    ):
        """Test executing tool call with invalid format"""
        tool_call = "not a dict"

        result = await tool_executor.execute_tool_and_get_result(
            tool_call, mock_tool_registry, mock_mcp_server, "session_123"
        )

        assert result["role"] == "tool"
        assert result["name"] == "unknown"

    def test_parse_tool_args_valid(self, tool_executor):
        """Test parsing valid tool arguments"""
        tool_call = {
            "function": {
                "name": "analyze_tempo",
                "arguments": '{"audio_file_id": "test.wav", "bpm": 120}',
            },
        }

        result = tool_executor._parse_tool_args(tool_call)

        assert result == {"audio_file_id": "test.wav", "bpm": 120}

    def test_parse_tool_args_dict_format(self, tool_executor):
        """Test parsing tool arguments that are already a dict"""
        tool_call = {
            "function": {"name": "analyze_tempo", "arguments": {"audio_file_id": "test.wav"}},
        }

        result = tool_executor._parse_tool_args(tool_call)

        assert result == {"audio_file_id": "test.wav"}

    def test_parse_tool_args_invalid_json(self, tool_executor):
        """Test parsing invalid JSON arguments"""
        tool_call = {
            "function": {"name": "analyze_tempo", "arguments": "invalid json{"},
        }

        result = tool_executor._parse_tool_args(tool_call)

        assert result == {}

    def test_parse_tool_args_invalid_format(self, tool_executor):
        """Test parsing tool call with invalid format"""
        tool_call = "not a dict"

        result = tool_executor._parse_tool_args(tool_call)

        assert result == {}

    def test_parse_tool_args_non_dict_result(self, tool_executor):
        """Test parsing tool arguments that aren't a dict after parsing"""
        tool_call = {
            "function": {"name": "analyze_tempo", "arguments": '"just a string"'},
        }

        result = tool_executor._parse_tool_args(tool_call)

        assert result == {}

    def test_enhance_file_not_found_error_midi_tool(self, tool_executor):
        """Test enhancing FileNotFoundError for MIDI tools"""
        error_msg = "MIDI file not found"
        result = tool_executor._enhance_file_not_found_error("midi_to_audio", error_msg)

        assert "Error" in result
        assert "validate_midi" in result

    def test_enhance_file_not_found_error_other_tool(self, tool_executor):
        """Test enhancing FileNotFoundError for other tools"""
        error_msg = "File not found"
        result = tool_executor._enhance_file_not_found_error("analyze_tempo", error_msg)

        assert result == "Error: File not found"
