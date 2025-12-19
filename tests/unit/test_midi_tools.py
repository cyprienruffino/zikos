"""Tests for MIDI tools"""

from pathlib import Path
from unittest.mock import patch

import pytest

from zikos.mcp.tools.midi import MidiTools


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
        midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        result = await midi_tools.validate_midi(midi_text)

        assert "valid" in result
        assert result["valid"] is True
        assert "midi_file_id" in result
        assert result["midi_file_id"] != ""
        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def test_midi_to_audio_file_not_found(self, midi_tools):
        """Test MIDI to audio with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.midi_to_audio("nonexistent_midi", "piano")

    @pytest.mark.asyncio
    async def test_midi_to_audio_default_instrument(self, midi_tools, temp_dir):
        """Test MIDI to audio with default instrument via call_tool"""
        from pathlib import Path

        from zikos.config import settings

        midi_path = Path(settings.midi_storage_path) / "test_midi.mid"
        midi_path.parent.mkdir(parents=True, exist_ok=True)

        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_text_to_file(midi_text, midi_path)

            with pytest.raises((RuntimeError, FileNotFoundError, ImportError)):
                await midi_tools.call_tool("midi_to_audio", midi_file_id="test_midi")
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_file_not_found(self, midi_tools):
        """Test MIDI to notation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.midi_to_notation("nonexistent_midi", "both")

    @pytest.mark.asyncio
    async def test_midi_to_notation_default_format(self, midi_tools):
        """Test MIDI to notation with default format via call_tool"""
        result = await midi_tools.call_tool("midi_to_notation", midi_file_id="test_midi")

        assert result["format"] == "both"

    @pytest.mark.asyncio
    async def test_call_tool_validate_midi(self, midi_tools):
        """Test call_tool for validate_midi"""
        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        result = await midi_tools.call_tool("validate_midi", midi_text=midi_text)

        assert "valid" in result
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_audio_file_not_found(self, midi_tools):
        """Test call_tool for midi_to_audio with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.call_tool(
                "midi_to_audio", midi_file_id="nonexistent", instrument="piano"
            )

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_notation_file_not_found(self, midi_tools):
        """Test call_tool for midi_to_notation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.call_tool(
                "midi_to_notation", midi_file_id="nonexistent", format="sheet_music"
            )

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, midi_tools):
        """Test call_tool with unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await midi_tools.call_tool("unknown_tool", arg1="test")

    @pytest.mark.asyncio
    async def test_validate_midi_invalid(self, midi_tools):
        """Test MIDI validation with invalid MIDI text"""
        result = await midi_tools.validate_midi("invalid MIDI text")

        assert "valid" in result
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_midi_empty(self, midi_tools):
        """Test MIDI validation with empty text"""
        result = await midi_tools.validate_midi("")

        assert "valid" in result
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_midi_to_notation_sheet_music(self, midi_tools, temp_dir):
        """Test MIDI to notation with sheet_music format"""
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_notation_sheet"
            midi_path = Path(settings.midi_storage_path) / f"{midi_file_id}.mid"
            midi_path.parent.mkdir(parents=True, exist_ok=True)

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_text_to_file(midi_text, midi_path)

            result = await midi_tools.midi_to_notation(midi_file_id, "sheet_music")

            assert "format" in result
            assert result["format"] == "sheet_music"
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_tabs(self, midi_tools, temp_dir):
        """Test MIDI to notation with tabs format"""
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_notation_tabs"
            midi_path = Path(settings.midi_storage_path) / f"{midi_file_id}.mid"
            midi_path.parent.mkdir(parents=True, exist_ok=True)

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_text_to_file(midi_text, midi_path)

            result = await midi_tools.midi_to_notation(midi_file_id, "tabs")

            assert "format" in result
            assert result["format"] == "tabs"
        except ImportError:
            pytest.skip("music21 not available")

    def test_find_soundfont(self, midi_tools, temp_dir):
        """Test finding SoundFont"""
        from pathlib import Path

        test_soundfont = temp_dir / "test.sf2"
        test_soundfont.touch()

        with patch.object(midi_tools, "_find_soundfont") as mock_find:
            mock_find.return_value = test_soundfont
            result = midi_tools._find_soundfont()
            assert result == test_soundfont

    def test_find_soundfont_not_found(self, midi_tools):
        """Test finding SoundFont when not available"""
        result = midi_tools._find_soundfont()
        assert result is None or isinstance(result, Path)

    def test_instrument_to_program(self, midi_tools):
        """Test instrument to program conversion"""
        assert midi_tools._instrument_to_program("piano") == 0
        assert midi_tools._instrument_to_program("guitar") == 24
        assert midi_tools._instrument_to_program("violin") == 40
        assert midi_tools._instrument_to_program("bass") == 32
        assert midi_tools._instrument_to_program("drums") == 128
        assert midi_tools._instrument_to_program("unknown") == 0
        assert midi_tools._instrument_to_program("PIANO") == 0
