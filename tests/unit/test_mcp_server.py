"""Tests for MCP server"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.mcp.server import MCPServer


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
        assert "create_metronome" in tool_names
        assert "create_tuner" in tool_names
        assert "create_chord_progression" in tool_names
        assert "create_tempo_trainer" in tool_names
        assert "create_ear_trainer" in tool_names
        assert "create_practice_timer" in tool_names

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
    async def test_call_tool_metronome_tool(self, mcp_server):
        """Test calling metronome tool"""
        with patch.object(mcp_server.metronome_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "metronome_created"}

            result = await mcp_server.call_tool("create_metronome", bpm=120, time_signature="4/4")

            assert "status" in result
            mock_call.assert_called_once_with("create_metronome", bpm=120, time_signature="4/4")

    @pytest.mark.asyncio
    async def test_call_tool_tuner_tool(self, mcp_server):
        """Test calling tuner tool"""
        with patch.object(mcp_server.tuner_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "tuner_created"}

            result = await mcp_server.call_tool("create_tuner", reference_frequency=440.0)

            assert "status" in result
            mock_call.assert_called_once_with("create_tuner", reference_frequency=440.0)

    @pytest.mark.asyncio
    async def test_call_tool_chord_progression_tool(self, mcp_server):
        """Test calling chord progression tool"""
        with patch.object(mcp_server.chord_progression_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "chord_progression_created"}

            result = await mcp_server.call_tool(
                "create_chord_progression", chords=["C", "G", "Am", "F"]
            )

            assert "status" in result
            mock_call.assert_called_once_with(
                "create_chord_progression", chords=["C", "G", "Am", "F"]
            )

    @pytest.mark.asyncio
    async def test_call_tool_tempo_trainer_tool(self, mcp_server):
        """Test calling tempo trainer tool"""
        with patch.object(mcp_server.tempo_trainer_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "tempo_trainer_created"}

            result = await mcp_server.call_tool("create_tempo_trainer", start_bpm=60, end_bpm=120)

            assert "status" in result
            mock_call.assert_called_once_with("create_tempo_trainer", start_bpm=60, end_bpm=120)

    @pytest.mark.asyncio
    async def test_call_tool_ear_trainer_tool(self, mcp_server):
        """Test calling ear trainer tool"""
        with patch.object(mcp_server.ear_trainer_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "ear_trainer_created"}

            result = await mcp_server.call_tool("create_ear_trainer", mode="intervals")

            assert "status" in result
            mock_call.assert_called_once_with("create_ear_trainer", mode="intervals")

    @pytest.mark.asyncio
    async def test_call_tool_practice_timer_tool(self, mcp_server):
        """Test calling practice timer tool"""
        with patch.object(mcp_server.practice_timer_tools, "call_tool") as mock_call:
            mock_call.return_value = {"status": "practice_timer_created"}

            result = await mcp_server.call_tool("create_practice_timer", duration_minutes=30)

            assert "status" in result
            mock_call.assert_called_once_with("create_practice_timer", duration_minutes=30)

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
