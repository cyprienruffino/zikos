"""Integration tests for MIDI tools with external dependencies"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


class TestMidiSynthesisIntegration:
    """Integration tests for MIDI synthesis with real FluidSynth"""

    @pytest.mark.asyncio
    async def test_midi_to_audio_with_fluidsynth(self, temp_dir):
        """Test MIDI to audio synthesis with real FluidSynth"""
        from zikos.config import settings
        from zikos.mcp.tools.processing.midi import MidiTools
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            from unittest.mock import patch

            midi_tools = MidiTools()
            midi_tools.storage_path = temp_dir

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
  E4 velocity=60 duration=0.5
  F4 velocity=60 duration=0.5
  G4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_file_id = "test_synth_integration"
            midi_path = temp_dir / f"{midi_file_id}.mid"
            midi_text_to_file(midi_text, midi_path)

            try:
                # Patch audio storage path BEFORE calling midi_to_audio
                with patch.object(settings, "audio_storage_path", str(temp_dir)):
                    result = await midi_tools.midi_to_audio(midi_file_id, "piano")

                    assert "audio_file_id" in result
                    assert result["audio_file_id"] != ""
                    assert "midi_file_id" in result
                    assert result["instrument"] == "piano"
                    assert "duration" in result
                    assert result["duration"] > 0
                    assert result["synthesis_method"] == "fluidsynth"

                    audio_path = temp_dir / f"{result['audio_file_id']}.wav"
                    assert audio_path.exists()
                    assert audio_path.stat().st_size > 0

            except (RuntimeError, FileNotFoundError, ImportError) as e:
                error_msg = str(e).lower()
                if "soundfont" in error_msg or "fluidsynth" in error_msg:
                    pytest.skip(f"FluidSynth/SoundFont not available: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_audio_different_instruments(self, temp_dir):
        """Test MIDI synthesis with different instruments"""
        from zikos.mcp.tools.processing.midi import MidiTools
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            midi_tools = MidiTools()
            midi_tools.storage_path = temp_dir

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_file_id = "test_instruments"
            midi_path = temp_dir / f"{midi_file_id}.mid"
            midi_text_to_file(midi_text, midi_path)

            instruments = ["piano", "guitar", "violin"]
            for instrument in instruments:
                try:
                    result = await midi_tools.midi_to_audio(midi_file_id, instrument)
                    assert result["instrument"] == instrument
                    assert result["audio_file_id"] != ""
                except (RuntimeError, FileNotFoundError, ImportError) as e:
                    error_msg = str(e).lower()
                    if "soundfont" in error_msg or "fluidsynth" in error_msg:
                        pytest.skip(f"FluidSynth/SoundFont not available: {e}")
                    raise
        except ImportError:
            pytest.skip("music21 not available")


class TestMidiNotationIntegration:
    """Integration tests for MIDI notation rendering with real music21"""

    @pytest.mark.asyncio
    async def test_midi_to_notation_sheet_music(self, temp_dir):
        """Test MIDI to notation rendering for sheet music"""
        from zikos.config import settings
        from zikos.mcp.tools.processing.midi import MidiTools
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            midi_tools = MidiTools()
            midi_tools.storage_path = temp_dir

            midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
  E4 velocity=60 duration=0.5
  F4 velocity=60 duration=0.5
  G4 velocity=60 duration=1.0
[/MIDI]
"""
            midi_file_id = "test_notation_sheet"
            midi_path = temp_dir / f"{midi_file_id}.mid"
            midi_text_to_file(midi_text, midi_path)

            try:
                result = await midi_tools.midi_to_notation(midi_file_id, "sheet_music")

                assert "midi_file_id" in result
                assert result["midi_file_id"] == midi_file_id
                assert "format" in result

                from unittest.mock import patch

                with patch.object(settings, "notation_storage_path", temp_dir):
                    if "sheet_music_url" in result:
                        sheet_path = temp_dir / f"sheet_{midi_file_id}.png"
                        if sheet_path.exists():
                            assert sheet_path.stat().st_size > 0
                    elif "sheet_music_error" in result:
                        error = result["sheet_music_error"]
                        if "lilypond" in error.lower() or "musescore" in error.lower():
                            pytest.skip(f"Notation rendering backend not available: {error}")
            except Exception as e:
                error_msg = str(e).lower()
                if "lilypond" in error_msg or "musescore" in error_msg:
                    pytest.skip(f"Notation rendering backend not available: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_both_formats(self, temp_dir):
        """Test MIDI to notation rendering for both formats"""
        from zikos.config import settings
        from zikos.mcp.tools.processing.midi import MidiTools
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            midi_tools = MidiTools()
            midi_tools.storage_path = temp_dir

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_file_id = "test_notation_both"
            midi_path = temp_dir / f"{midi_file_id}.mid"
            midi_text_to_file(midi_text, midi_path)

            try:
                result = await midi_tools.midi_to_notation(midi_file_id, "both")

                assert "midi_file_id" in result
                assert result["format"] == "both"

                notation_path = Path(settings.notation_storage_path)
                if "sheet_music_url" in result:
                    sheet_path = notation_path / f"sheet_{midi_file_id}.png"
                    if sheet_path.exists():
                        assert sheet_path.stat().st_size > 0
            except Exception as e:
                error_msg = str(e).lower()
                if "lilypond" in error_msg or "musescore" in error_msg:
                    pytest.skip(f"Notation rendering backend not available: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")


class TestMidiFullPipeline:
    """Integration tests for full MIDI pipeline"""

    @pytest.mark.asyncio
    async def test_full_midi_pipeline(self, temp_dir):
        """Test full pipeline: validate → synthesize → render"""
        from zikos.config import settings
        from zikos.mcp.tools.processing.midi import MidiTools

        try:
            midi_tools = MidiTools()
            midi_tools.storage_path = temp_dir

            midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
  E4 velocity=60 duration=0.5
  F4 velocity=60 duration=0.5
  G4 velocity=60 duration=0.5
  A4 velocity=60 duration=0.5
  B4 velocity=60 duration=0.5
  C5 velocity=60 duration=1.0
[/MIDI]
"""

            validate_result = await midi_tools.validate_midi(midi_text)
            assert validate_result["valid"] is True
            midi_file_id = validate_result["midi_file_id"]

            try:
                synth_result = await midi_tools.midi_to_audio(midi_file_id, "piano")
                assert "audio_file_id" in synth_result
                assert synth_result["audio_file_id"] != ""
            except (RuntimeError, FileNotFoundError, ImportError) as e:
                error_msg = str(e).lower()
                if "soundfont" in error_msg or "fluidsynth" in error_msg:
                    pytest.skip(f"FluidSynth/SoundFont not available: {e}")
                raise

            try:
                notation_result = await midi_tools.midi_to_notation(midi_file_id, "both")
                assert "midi_file_id" in notation_result
                assert notation_result["midi_file_id"] == midi_file_id
            except Exception as e:
                error_msg = str(e).lower()
                if "lilypond" in error_msg or "musescore" in error_msg:
                    pytest.skip(f"Notation rendering backend not available: {e}")
                raise

        except ImportError:
            pytest.skip("music21 not available")
