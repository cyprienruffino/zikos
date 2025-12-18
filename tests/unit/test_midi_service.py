"""Tests for MIDI service"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.zikos.services.midi import MidiService


@pytest.fixture
def midi_service(temp_dir):
    """Create MidiService instance with temp directory"""
    with patch("src.zikos.config.settings") as mock_settings:
        mock_settings.midi_storage_path = temp_dir
        mock_settings.notation_storage_path = temp_dir
        service = MidiService()
        service.storage_path = temp_dir
        service.notation_path = temp_dir
        return service


class TestMidiService:
    """Tests for MidiService"""

    @pytest.mark.asyncio
    async def test_validate_midi(self, midi_service):
        """Test MIDI validation"""
        with patch.object(midi_service.midi_tools, "validate_midi") as mock_validate:
            mock_validate.return_value = {"valid": True, "midi_file_id": "test"}

            result = await midi_service.validate_midi("[MIDI]C4[/MIDI]")

            assert "valid" in result
            mock_validate.assert_called_once_with("[MIDI]C4[/MIDI]")

    @pytest.mark.asyncio
    async def test_synthesize(self, midi_service, temp_dir):
        """Test MIDI synthesis"""
        midi_file_id = "test_midi"
        test_file = temp_dir / f"{midi_file_id}.mid"
        test_file.touch()

        with patch.object(midi_service.midi_tools, "midi_to_audio") as mock_synth:
            mock_synth.return_value = {"audio_file_id": "test_audio"}

            result = await midi_service.synthesize(midi_file_id, "piano")

            assert isinstance(result, str)
            assert result == "test_audio"

    @pytest.mark.asyncio
    async def test_render_notation(self, midi_service, temp_dir):
        """Test notation rendering"""
        midi_file_id = "test_midi"
        test_file = temp_dir / f"{midi_file_id}.mid"
        test_file.touch()

        with patch.object(midi_service.midi_tools, "midi_to_notation") as mock_render:
            mock_render.return_value = {
                "sheet_music_url": "/notation/sheet.png",
                "tabs_url": "/notation/tabs.png",
            }

            result = await midi_service.render_notation(midi_file_id, "both")

            assert "sheet_music_url" in result
            mock_render.assert_called_once_with(str(test_file), "both")

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
