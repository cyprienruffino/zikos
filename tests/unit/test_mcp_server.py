"""Tests for MCP server"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.zikos.mcp.server import MCPServer


@pytest.fixture
def mcp_server():
    """Create MCPServer instance"""
    return MCPServer()


class TestMCPServer:
    """Tests for MCPServer"""

    def test_get_tools(self, mcp_server):
        """Test getting all tool schemas"""
        tools = mcp_server.get_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        tool_names = [t["function"]["name"] for t in tools if "function" in t]
        assert "analyze_tempo" in tool_names
        assert "request_audio_recording" in tool_names

    @pytest.mark.asyncio
    async def test_call_tool_audio_tool(self, mcp_server):
        """Test calling audio tool"""
        with patch.object(mcp_server.audio_tools, "call_tool") as mock_call:
            mock_call.return_value = {"bpm": 120.0}

            result = await mcp_server.call_tool("analyze_tempo", audio_file_id="test")

            assert "bpm" in result
            mock_call.assert_called_once_with("analyze_tempo", audio_file_id="test")

    @pytest.mark.asyncio
    async def test_call_tool_midi_tool(self, mcp_server):
        """Test calling MIDI tool"""
        with patch.object(mcp_server.midi_tools, "call_tool") as mock_call:
            mock_call.return_value = {"valid": True}

            result = await mcp_server.call_tool("midi_validate", midi_text="test")

            assert "valid" in result
            mock_call.assert_called_once_with("midi_validate", midi_text="test")

    @pytest.mark.asyncio
    async def test_call_tool_recording_tool(self, mcp_server):
        """Test calling recording tool"""
        with patch.object(mcp_server.recording_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "recording_requested"}

            result = await mcp_server.call_tool("recording_request", prompt="test")

            assert "status" in result
            mock_call.assert_called_once_with("recording_request", prompt="test")

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, mcp_server):
        """Test calling unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await mcp_server.call_tool("unknown_tool", arg1="test")
