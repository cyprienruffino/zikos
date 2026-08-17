"""Unit tests for audio API endpoints"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from zikos.constants import UploadConstants
from zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_audio_service():
    """Mock audio service"""
    with patch("zikos.api.audio.audio_service") as mock:
        mock.store_audio = AsyncMock(return_value="11111111-1111-4111-8111-111111111111")
        mock.run_baseline_analysis = AsyncMock(return_value={"tempo": {}})
        yield mock


class TestUploadLimits:
    """Tests for upload size and type validation"""

    def test_upload_rejects_disallowed_extension(self, client, mock_audio_service):
        response = client.post(
            "/api/audio/upload",
            files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
        )
        assert response.status_code == 415
        mock_audio_service.store_audio.assert_not_called()

    def test_upload_rejects_disallowed_content_type(self, client, mock_audio_service):
        response = client.post(
            "/api/audio/upload",
            files={"file": ("song.wav", b"RIFF....", "text/html")},
        )
        assert response.status_code == 415
        mock_audio_service.store_audio.assert_not_called()

    def test_upload_rejects_oversized_file(self, client, mock_audio_service):
        with patch.object(UploadConstants, "MAX_UPLOAD_SIZE_BYTES", 10):
            response = client.post(
                "/api/audio/upload",
                files={"file": ("song.wav", b"x" * 100, "audio/wav")},
            )
        assert response.status_code == 413
        mock_audio_service.store_audio.assert_not_called()

    def test_upload_accepts_valid_audio(self, client, mock_audio_service):
        response = client.post(
            "/api/audio/upload",
            files={"file": ("song.wav", b"RIFF....", "audio/wav")},
        )
        assert response.status_code == 200
        assert response.json()["audio_file_id"] == "11111111-1111-4111-8111-111111111111"

    def test_upload_accepts_webm_video_content_type(self, client, mock_audio_service):
        """Browsers report MediaRecorder output as video/webm."""
        response = client.post(
            "/api/audio/upload",
            files={"file": ("recording.webm", b"\x1a\x45\xdf\xa3", "video/webm")},
        )
        assert response.status_code == 200
