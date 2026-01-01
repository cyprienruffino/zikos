"""Integration tests for music21 library

These tests verify that music21 integration works correctly when implemented.
Currently, MIDI tools are stubs, but this file provides the structure for
future music21 integration tests.

These tests will be skipped if music21 is not actually used in the implementation.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


class TestMusic21Integration:
    """Integration tests for music21 library

    Note: These tests are placeholders for when music21 is actually implemented.
    The MIDI tools currently return stub data.
    """

    @pytest.mark.asyncio
    async def test_music21_import(self):
        """Test that music21 can be imported"""
        try:
            import music21

            assert music21 is not None
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_validate_with_music21(self, temp_dir):
        """Test MIDI validation using music21 (when implemented)"""
        from zikos.mcp.tools.processing.midi import MidiTools

        tools = MidiTools()
        result = await tools.validate_midi("[MIDI]C4[/MIDI]")

        assert "valid" in result
        assert isinstance(result["valid"], bool)

        if result.get("valid"):
            assert "midi_file_id" in result
            assert "errors" in result
            assert "warnings" in result
            assert isinstance(result["errors"], list)
            assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def test_midi_to_notation_with_music21(self, temp_dir):
        """Test MIDI to notation rendering using music21 (when implemented)"""
        from unittest.mock import patch

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi import MidiTools
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "notation_storage_path", temp_dir):
                    tools = MidiTools()
                    with patch.object(tools, "storage_path", temp_dir):
                        midi_file_id = "test_midi"
                        midi_path = temp_dir / f"{midi_file_id}.mid"

                        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                        midi_text_to_file(midi_text, midi_path)

                        result = await tools.midi_to_notation(midi_file_id, "both")

                        assert "midi_file_id" in result
                        assert "format" in result

                        if "sheet_music_url" in result:
                            assert isinstance(result["sheet_music_url"], str)
                        if "tabs_url" in result:
                            assert isinstance(result["tabs_url"], str)
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_music21_stream_creation(self):
        """Test creating a music21 stream (basic functionality)"""
        try:
            from music21 import note, stream

            s = stream.Stream()
            n = note.Note("C4")
            s.append(n)

            assert len(s) == 1
            assert s[0].pitch.name == "C"
            assert s[0].pitch.octave == 4
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_music21_key_detection(self):
        """Test music21 key detection functionality"""
        try:
            from music21 import key, note, stream

            s = stream.Stream()
            for pitch_name in ["C", "E", "G"]:
                n = note.Note(pitch_name + "4")
                s.append(n)

            detected_key = s.analyze("key")
            assert detected_key is not None
        except ImportError:
            pytest.skip("music21 not available")
        except AttributeError:
            pytest.skip("music21 key analysis not available in this version")

    @pytest.mark.asyncio
    async def test_music21_midi_export(self, temp_dir):
        """Test music21 MIDI export functionality"""
        try:
            from music21 import midi, note, stream

            s = stream.Stream()
            n = note.Note("C4", quarterLength=1.0)
            s.append(n)

            midi_path = temp_dir / "test_music21.mid"
            s.write("midi", fp=str(midi_path))

            assert midi_path.exists()
            assert midi_path.stat().st_size > 0
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_music21_midi_import(self, temp_dir):
        """Test music21 MIDI import functionality"""
        try:
            from music21 import midi, note, stream

            s = stream.Stream()
            n = note.Note("C4", quarterLength=1.0)
            s.append(n)

            midi_path = temp_dir / "test_import.mid"
            s.write("midi", fp=str(midi_path))

            imported = midi.translate.midiFilePathToStream(str(midi_path))
            assert imported is not None
            assert len(imported.flat.notes) > 0
        except ImportError:
            pytest.skip("music21 not available")
