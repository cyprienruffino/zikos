"""Tests for MIDI tools"""

import pytest

from src.zikos.mcp.tools.midi import MidiTools


@pytest.fixture
def midi_tools():
    """Create MidiTools instance"""
    return MidiTools()


class TestMidiTools:
    """Tests for MidiTools"""

    def test_get_tool_schemas(self, midi_tools):
        """Test getting tool schemas"""
        schemas = midi_tools.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 3

        tool_names = [s["function"]["name"] for s in schemas]
        assert "validate_midi" in tool_names
        assert "midi_to_audio" in tool_names
        assert "midi_to_notation" in tool_names

    @pytest.mark.asyncio
    async def test_validate_midi(self, midi_tools):
        """Test MIDI validation"""
        result = await midi_tools.validate_midi("[MIDI]C4[/MIDI]")

        assert "valid" in result
        assert result["valid"] is True
        assert "midi_file_id" in result
        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def test_midi_to_audio(self, midi_tools):
        """Test MIDI to audio synthesis"""
        result = await midi_tools.midi_to_audio("test_midi", "piano")

        assert "audio_file_id" in result
        assert isinstance(result["audio_file_id"], str)

    @pytest.mark.asyncio
    async def test_midi_to_audio_default_instrument(self, midi_tools):
        """Test MIDI to audio with default instrument via call_tool"""
        result = await midi_tools.call_tool("midi_to_audio", midi_file_id="test_midi")

        assert "audio_file_id" in result

    @pytest.mark.asyncio
    async def test_midi_to_notation(self, midi_tools):
        """Test MIDI to notation rendering"""
        result = await midi_tools.midi_to_notation("test_midi", "both")

        assert "midi_file_id" in result
        assert result["midi_file_id"] == "test_midi"
        assert "sheet_music_url" in result
        assert "tabs_url" in result
        assert result["format"] == "both"

    @pytest.mark.asyncio
    async def test_midi_to_notation_default_format(self, midi_tools):
        """Test MIDI to notation with default format via call_tool"""
        result = await midi_tools.call_tool("midi_to_notation", midi_file_id="test_midi")

        assert result["format"] == "both"

    @pytest.mark.asyncio
    async def test_call_tool_validate_midi(self, midi_tools):
        """Test call_tool for validate_midi"""
        result = await midi_tools.call_tool("validate_midi", midi_text="[MIDI]C4[/MIDI]")

        assert "valid" in result

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_audio(self, midi_tools):
        """Test call_tool for midi_to_audio"""
        result = await midi_tools.call_tool(
            "midi_to_audio", midi_file_id="test", instrument="piano"
        )

        assert "audio_file_id" in result

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_audio_default_instrument(self, midi_tools):
        """Test call_tool for midi_to_audio with default instrument"""
        result = await midi_tools.call_tool("midi_to_audio", midi_file_id="test")

        assert "audio_file_id" in result

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_notation(self, midi_tools):
        """Test call_tool for midi_to_notation"""
        result = await midi_tools.call_tool(
            "midi_to_notation", midi_file_id="test", format="sheet_music"
        )

        assert "midi_file_id" in result

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, midi_tools):
        """Test call_tool with unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await midi_tools.call_tool("unknown_tool", arg1="test")
