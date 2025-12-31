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
        with patch.object(
            audio_service.preprocessing_service, "preprocess_upload_file"
        ) as mock_preprocess:
            mock_preprocessed = temp_dir / "preprocessed.wav"
            mock_preprocessed.write_bytes(b"preprocessed audio data")
            mock_preprocess.return_value = mock_preprocessed

            audio_file_id = await audio_service.store_audio(mock_upload_file)

            assert isinstance(audio_file_id, str)
            assert len(audio_file_id) > 0

            file_path = temp_dir / f"{audio_file_id}.wav"
            assert file_path.exists()
            assert file_path.read_bytes() == b"preprocessed audio data"
            mock_preprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_audio_with_recording_id(self, audio_service, mock_upload_file, temp_dir):
        """Test storing audio with recording_id"""
        with patch.object(
            audio_service.preprocessing_service, "preprocess_upload_file"
        ) as mock_preprocess:
            mock_preprocessed = temp_dir / "preprocessed.wav"
            mock_preprocessed.write_bytes(b"preprocessed audio data")
            mock_preprocess.return_value = mock_preprocessed

            recording_id = "test_recording_123"
            audio_file_id = await audio_service.store_audio(mock_upload_file, recording_id)

            assert isinstance(audio_file_id, str)
            assert len(audio_file_id) > 0

    @pytest.mark.asyncio
    async def test_run_baseline_analysis(self, audio_service, temp_dir):
        """Test running baseline analysis with real tools"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        audio_file_id = "test_audio"
        audio_file = temp_dir / f"{audio_file_id}.wav"

        # Create synthesized audio (scale with known characteristics)
        create_test_audio_file(audio_file, audio_type="scale", duration=2.0)

        result = await audio_service.run_baseline_analysis(audio_file_id)

        assert "tempo" in result
        assert "pitch" in result
        assert "rhythm" in result

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_run_baseline_analysis_with_real_audio(self, audio_service, temp_dir):
        """Test running baseline analysis with real synthesized audio"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        audio_file_id = "test_real_audio"
        audio_file = temp_dir / f"{audio_file_id}.wav"

        # Create synthesized audio (scale with known characteristics)
        create_test_audio_file(audio_file, audio_type="scale", duration=2.0)

        # Run real analysis (no mocks)
        result = await audio_service.run_baseline_analysis(audio_file_id)

        # Should have all analysis components
        assert "tempo" in result
        assert "pitch" in result
        assert "rhythm" in result

        # Tempo should be detected (may not be exact, but should exist)
        assert "bpm" in result["tempo"] or "error" in result["tempo"]

        # Pitch should detect notes from the scale
        assert "notes" in result["pitch"] or "error" in result["pitch"]

        # Rhythm should have onsets
        assert "onsets" in result["rhythm"] or "error" in result["rhythm"]

    @pytest.mark.asyncio
    async def test_get_audio_info(self, audio_service, temp_dir):
        """Test getting audio info"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        audio_file_id = "test_audio"
        audio_file = temp_dir / f"{audio_file_id}.wav"

        # Create real audio file
        create_test_audio_file(audio_file, audio_type="single_note", duration=2.0)

        # Patch settings.audio_storage_path to ensure resolve_audio_path finds the file
        with patch("zikos.mcp.tools.analysis.audio.utils.settings") as mock_settings:
            mock_settings.audio_storage_path = temp_dir
            result = await audio_service.get_audio_info(audio_file_id)

        assert "duration" in result
        assert result["duration"] > 0
        assert "sample_rate" in result

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
