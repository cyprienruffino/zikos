"""Tests for MCP server"""

import pytest

from zikos.mcp.server import MCPServer
from zikos.mcp.tool import ToolCategory
from zikos.mcp.tool_registry import ToolRegistry


@pytest.fixture
def mcp_server():
    return MCPServer()


class TestMCPServer:
    def test_get_tools_returns_all_registered_tools(self, mcp_server):
        tools = mcp_server.get_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        tool_names = [t["function"]["name"] for t in tools if "function" in t]
        assert "analyze_tempo" in tool_names
        assert "get_audio_info" in tool_names
        assert "request_audio_recording" in tool_names
        assert "create_metronome" in tool_names
        assert "create_tuner" in tool_names
        assert "create_chord_progression" in tool_names
        assert "create_tempo_trainer" in tool_names
        assert "create_ear_trainer" in tool_names
        assert "create_practice_timer" in tool_names

    def test_get_tool_registry_returns_real_registry(self, mcp_server):
        registry = mcp_server.get_tool_registry()

        assert isinstance(registry, ToolRegistry)
        assert registry.get_tool("analyze_tempo") is not None
        assert registry.get_tool("create_metronome") is not None
        assert registry.get_tool("nonexistent") is None

    def test_tool_categories_are_correct(self, mcp_server):
        registry = mcp_server.get_tool_registry()

        assert registry.get_tool("analyze_tempo").category == ToolCategory.AUDIO_ANALYSIS
        assert registry.get_tool("create_metronome").category == ToolCategory.DISPLAY_WIDGET
        assert (
            registry.get_tool("request_audio_recording").category
            == ToolCategory.INTERACTION_REQUEST
        )

    @pytest.mark.asyncio
    async def test_call_metronome_tool(self, mcp_server):
        result = await mcp_server.call_tool("create_metronome", bpm=140, time_signature="3/4")

        assert result["status"] == "metronome_created"
        assert result["bpm"] == 140
        assert result["time_signature"] == "3/4"
        assert "metronome_id" in result

    @pytest.mark.asyncio
    async def test_call_tuner_tool(self, mcp_server):
        result = await mcp_server.call_tool("create_tuner", reference_frequency=442.0)

        assert result["status"] == "tuner_created"
        assert result["reference_frequency"] == 442.0

    @pytest.mark.asyncio
    async def test_call_chord_progression_tool(self, mcp_server):
        result = await mcp_server.call_tool(
            "create_chord_progression", chords=["C", "G", "Am", "F"]
        )

        assert result["status"] == "chord_progression_created"
        assert result["chords"] == ["C", "G", "Am", "F"]

    @pytest.mark.asyncio
    async def test_call_tempo_trainer_tool(self, mcp_server):
        result = await mcp_server.call_tool("create_tempo_trainer", start_bpm=60, end_bpm=120)

        assert result["status"] == "tempo_trainer_created"
        assert result["start_bpm"] == 60
        assert result["end_bpm"] == 120

    @pytest.mark.asyncio
    async def test_call_ear_trainer_tool(self, mcp_server):
        result = await mcp_server.call_tool("create_ear_trainer", mode="intervals")

        assert result["status"] == "ear_trainer_created"

    @pytest.mark.asyncio
    async def test_call_practice_timer_tool(self, mcp_server):
        result = await mcp_server.call_tool("create_practice_timer", duration_minutes=30)

        assert result["status"] == "practice_timer_created"
        assert result["duration_minutes"] == 30

    @pytest.mark.asyncio
    async def test_call_recording_tool(self, mcp_server):
        result = await mcp_server.call_tool("request_audio_recording", prompt="Play a C scale")

        assert result["status"] == "recording_requested"
        assert "Play a C scale" in result["prompt"]

    @pytest.mark.asyncio
    async def test_call_unknown_tool_returns_error_dict(self, mcp_server):
        """Unknown tools return the documented error shape, not a raised exception"""
        result = await mcp_server.call_tool("nonexistent_tool", arg="value")

        assert result["error"] is True
        assert result["error_type"] == "UNKNOWN_TOOL"
        assert "nonexistent_tool" in result["message"]

    @pytest.mark.asyncio
    async def test_call_tool_normalizes_missing_kwargs(self, mcp_server):
        """KeyError from missing required kwargs becomes a MISSING_PARAMETER error dict"""
        result = await mcp_server.call_tool("validate_midi")  # no midi_text

        assert result["error"] is True
        assert result["error_type"] == "MISSING_PARAMETER"
        assert "midi_text" in result["message"]

    @pytest.mark.asyncio
    async def test_call_tool_normalizes_file_not_found(self, mcp_server):
        """FileNotFoundError raised by MIDI tools becomes a FILE_NOT_FOUND error dict"""
        result = await mcp_server.call_tool(
            "midi_to_audio", midi_file_id="nonexistent", instrument="piano"
        )

        assert result["error"] is True
        assert result["error_type"] == "FILE_NOT_FOUND"
        assert "validate_midi" in result["message"]  # helpful message preserved

    @pytest.mark.asyncio
    async def test_metronome_rejects_bad_params(self, mcp_server):
        result = await mcp_server.call_tool("create_metronome", bpm=1000)
        assert result["error"] is True
        assert result["error_type"] == "INVALID_PARAMETER"

        result = await mcp_server.call_tool("create_metronome", time_signature="waltz")
        assert result["error"] is True
        assert result["error_type"] == "INVALID_PARAMETER"

    @pytest.mark.asyncio
    async def test_tempo_trainer_rejects_bad_params(self, mcp_server):
        result = await mcp_server.call_tool("create_tempo_trainer", start_bpm=120, end_bpm=60)
        assert result["error"] is True
        assert result["error_type"] == "INVALID_PARAMETER"
        assert "start_bpm" in result["message"]

        result = await mcp_server.call_tool(
            "create_tempo_trainer", start_bpm=60, end_bpm=120, ramp_type="wibbly"
        )
        assert result["error"] is True

        result = await mcp_server.call_tool(
            "create_tempo_trainer", start_bpm=60, end_bpm=120, duration_minutes=-1
        )
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_tuner_rejects_bad_reference_frequency(self, mcp_server):
        result = await mcp_server.call_tool("create_tuner", reference_frequency=-440.0)
        assert result["error"] is True
        assert result["error_type"] == "INVALID_PARAMETER"

    @pytest.mark.asyncio
    async def test_routing_goes_through_registry(self, mcp_server):
        """Verify call_tool routes through the registry, not hardcoded dispatch."""
        registry = mcp_server.get_tool_registry()
        collection = registry.get_collection_for_tool("create_metronome")

        assert collection is mcp_server.metronome_tools
