"""Tests for audio service"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.services.audio import AudioService


@pytest.fixture
def audio_service(temp_dir):
    """Create AudioService instance with temp directory"""
    with patch("zikos.config.settings") as mock_settings:
        mock_settings.audio_storage_path = temp_dir
        service = AudioService()
        service.storage_path = temp_dir
        return service


@pytest.fixture
def mock_upload_file():
    """Create mock UploadFile"""
    file = MagicMock()
    file.read = AsyncMock(return_value=b"fake audio data")
    file.filename = "test.wav"
    return file


class TestAudioService:
    """Tests for AudioService"""

    @pytest.mark.asyncio
    async def test_store_audio(self, audio_service, mock_upload_file, temp_dir):
        """Test storing audio file"""
        audio_file_id = await audio_service.store_audio(mock_upload_file)

        assert isinstance(audio_file_id, str)
        assert len(audio_file_id) > 0

        file_path = temp_dir / f"{audio_file_id}.wav"
        assert file_path.exists()
        assert file_path.read_bytes() == b"fake audio data"

    @pytest.mark.asyncio
    async def test_store_audio_with_recording_id(self, audio_service, mock_upload_file):
        """Test storing audio with recording_id"""
        recording_id = "test_recording_123"
        audio_file_id = await audio_service.store_audio(mock_upload_file, recording_id)

        assert isinstance(audio_file_id, str)
        assert len(audio_file_id) > 0

    @pytest.mark.asyncio
    async def test_run_baseline_analysis(self, audio_service, temp_dir):
        """Test running baseline analysis"""
        audio_file_id = "test_audio"
        test_file = temp_dir / f"{audio_file_id}.wav"
        test_file.touch()

        with (
            patch.object(audio_service.analysis_tools, "analyze_tempo") as mock_tempo,
            patch.object(audio_service.analysis_tools, "detect_pitch") as mock_pitch,
            patch.object(audio_service.analysis_tools, "analyze_rhythm") as mock_rhythm,
        ):
            mock_tempo.return_value = {"bpm": 120.0}
            mock_pitch.return_value = {"notes": []}
            mock_rhythm.return_value = {"onsets": []}

            result = await audio_service.run_baseline_analysis(audio_file_id)

            assert "tempo" in result
            assert "pitch" in result
            assert "rhythm" in result
            mock_tempo.assert_called_once_with(audio_file_id)
            mock_pitch.assert_called_once_with(audio_file_id)
            mock_rhythm.assert_called_once_with(audio_file_id)

    @pytest.mark.asyncio
    async def test_get_audio_info(self, audio_service, temp_dir):
        """Test getting audio info"""
        audio_file_id = "test_audio"
        test_file = temp_dir / f"{audio_file_id}.wav"
        test_file.touch()

        with patch.object(audio_service.analysis_tools, "get_audio_info") as mock_info:
            mock_info.return_value = {
                "duration": 10.5,
                "sample_rate": 44100,
            }

            result = await audio_service.get_audio_info(audio_file_id)

            assert "duration" in result
            mock_info.assert_called_once_with(audio_file_id)

    @pytest.mark.asyncio
    async def test_get_audio_path(self, audio_service, temp_dir):
        """Test getting audio path"""
        audio_file_id = "test_audio"
        test_file = temp_dir / f"{audio_file_id}.wav"
        test_file.touch()

        path = await audio_service.get_audio_path(audio_file_id)

        assert path == test_file
        assert path.exists()

    @pytest.mark.asyncio
    async def test_get_audio_path_not_found(self, audio_service):
        """Test getting audio path when file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            await audio_service.get_audio_path("nonexistent")
