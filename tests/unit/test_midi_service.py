"""Tests for MIDI service"""

from pathlib import Path

import pytest

from zikos.services.midi import MidiService


@pytest.fixture
def midi_service(temp_dir):
    """Create MidiService instance with temp directory"""
    from unittest.mock import patch

    with patch("zikos.config.settings") as mock_settings:
        mock_settings.midi_storage_path = temp_dir
        mock_settings.notation_storage_path = temp_dir
        mock_settings.audio_storage_path = temp_dir
        service = MidiService()
        service.storage_path = temp_dir
        service.notation_path = temp_dir
        service.midi_tools.storage_path = temp_dir
        return service


class TestMidiService:
    """Tests for MidiService"""

    @pytest.mark.asyncio
    async def test_validate_midi(self, midi_service):
        """Test MIDI validation with real implementation"""
        midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
[/MIDI]
"""
        result = await midi_service.validate_midi(midi_text)

        assert "valid" in result
        assert result["valid"] is True
        assert "midi_file_id" in result
        assert result["midi_file_id"] != ""
        assert "errors" in result
        assert isinstance(result["errors"], list)

        midi_file_id = result["midi_file_id"]
        midi_path = midi_service.storage_path / f"{midi_file_id}.mid"
        assert midi_path.exists()

    @pytest.mark.asyncio
    async def test_validate_midi_invalid(self, midi_service):
        """Test MIDI validation with invalid input"""
        result = await midi_service.validate_midi("invalid MIDI text")

        assert "valid" in result
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_synthesize(self, midi_service, temp_dir):
        """Test MIDI synthesis with real implementation"""
        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_synth"
            midi_path = temp_dir / f"{midi_file_id}.mid"
            midi_text_to_file(midi_text, midi_path)

            try:
                result = await midi_service.synthesize(midi_file_id, "piano")
                assert isinstance(result, str)
                assert result != ""

                audio_path = temp_dir / f"{result}.wav"
                if audio_path.exists():
                    assert audio_path.stat().st_size > 0
            except (RuntimeError, FileNotFoundError, ImportError) as e:
                if "SoundFont" in str(e) or "fluidsynth" in str(e).lower():
                    pytest.skip(f"Skipping synthesis test: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_render_notation(self, midi_service, temp_dir):
        """Test notation rendering with real implementation"""
        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
  E4 velocity=60 duration=0.5
[/MIDI]
"""
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_notation"
            midi_path = temp_dir / f"{midi_file_id}.mid"
            midi_text_to_file(midi_text, midi_path)

            try:
                result = await midi_service.render_notation(midi_file_id, "both")

                assert "midi_file_id" in result
                assert result["midi_file_id"] == midi_file_id
                assert "format" in result

                if "sheet_music_url" in result:
                    sheet_path = temp_dir / f"sheet_{midi_file_id}.png"
                    if sheet_path.exists():
                        assert sheet_path.stat().st_size > 0
            except Exception as e:
                if "lilypond" in str(e).lower() or "musescore" in str(e).lower():
                    pytest.skip(f"Skipping notation test: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_get_midi_path(self, midi_service, temp_dir):
        """Test getting MIDI path"""
        midi_file_id = "test_midi"
        test_file = temp_dir / f"{midi_file_id}.mid"
        test_file.touch()

        path = await midi_service.get_midi_path(midi_file_id)

        assert path == test_file
        assert path.exists()

    @pytest.mark.asyncio
    async def test_get_midi_path_not_found(self, midi_service):
        """Test getting MIDI path when file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            await midi_service.get_midi_path("nonexistent")
