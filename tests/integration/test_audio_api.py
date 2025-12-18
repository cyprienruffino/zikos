"""Integration tests for audio API"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAudioAPI:
    """Tests for audio API endpoints"""

    def test_upload_audio(self, client, temp_dir):
        """Test uploading audio file"""
        with patch("src.zikos.api.audio.audio_service") as mock_service:
            mock_service.store_audio = AsyncMock(return_value="test_audio_id")
            mock_service.run_baseline_analysis = AsyncMock(
                return_value={
                    "tempo": {"bpm": 120.0},
                    "pitch": {"notes": []},
                    "rhythm": {"onsets": []},
                }
            )

            response = client.post(
                "/api/audio/upload",
                files={"file": ("test.wav", b"fake audio data", "audio/wav")},
                data={"recording_id": "test_recording"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "audio_file_id" in data
            assert "analysis" in data

    def test_upload_audio_error(self, client):
        """Test uploading audio with error"""
        with patch("src.zikos.api.audio.audio_service") as mock_service:
            mock_service.store_audio = AsyncMock(side_effect=Exception("Storage failed"))

            response = client.post(
                "/api/audio/upload",
                files={"file": ("test.wav", b"fake audio data", "audio/wav")},
            )

            assert response.status_code == 500

    def test_get_audio_info(self, client):
        """Test getting audio info"""
        with patch("src.zikos.api.audio.audio_service") as mock_service:
            mock_service.get_audio_info = AsyncMock(
                return_value={
                    "duration": 10.5,
                    "sample_rate": 44100,
                }
            )

            response = client.get("/api/audio/test_audio_id/info")

            assert response.status_code == 200
            data = response.json()
            assert "duration" in data
            assert data["duration"] == 10.5

    def test_get_audio_info_not_found(self, client):
        """Test getting audio info for non-existent file"""
        with patch("src.zikos.api.audio.audio_service") as mock_service:
            mock_service.get_audio_info = AsyncMock(side_effect=Exception("Not found"))

            response = client.get("/api/audio/nonexistent/info")

            assert response.status_code == 404

    def test_get_audio_file(self, client, temp_dir):
        """Test getting audio file"""
        test_file = temp_dir / "test_audio.wav"
        test_file.write_bytes(b"fake audio data")

        with patch("src.zikos.api.audio.audio_service") as mock_service:
            mock_service.get_audio_path = AsyncMock(return_value=test_file)

            response = client.get("/api/audio/test_audio")

            assert response.status_code == 200
            assert (
                "audio" in response.headers["content-type"]
                or "application" in response.headers["content-type"]
            )

    def test_get_audio_file_not_found(self, client):
        """Test getting non-existent audio file"""
        with patch("src.zikos.api.audio.audio_service") as mock_service:
            mock_service.get_audio_path = AsyncMock(side_effect=Exception("Not found"))

            response = client.get("/api/audio/nonexistent")

            assert response.status_code == 404
