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


class TestAudioIdValidation:
    """Path IDs must be UUIDs before touching the filesystem"""

    def test_get_audio_rejects_non_uuid_id(self, client, mock_audio_service):
        mock_audio_service.get_audio_path = AsyncMock()
        response = client.get("/api/audio/..%5Csecret")
        assert response.status_code == 400
        mock_audio_service.get_audio_path.assert_not_called()

    def test_get_audio_info_rejects_non_uuid_id(self, client, mock_audio_service):
        mock_audio_service.get_audio_info = AsyncMock()
        response = client.get("/api/audio/not-a-uuid/info")
        assert response.status_code == 400
        mock_audio_service.get_audio_info.assert_not_called()

    def test_get_audio_accepts_uuid(self, client, mock_audio_service, temp_dir):
        test_file = temp_dir / "a.wav"
        test_file.write_bytes(b"RIFF")
        mock_audio_service.get_audio_path = AsyncMock(return_value=test_file)
        response = client.get("/api/audio/33333333-3333-4333-8333-333333333333")
        assert response.status_code == 200
