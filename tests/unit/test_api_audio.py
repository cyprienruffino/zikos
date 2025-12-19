"""Unit tests for audio API endpoints"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from zikos.api.audio import router
from zikos.main import app

app.include_router(router, prefix="/api/audio")


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_audio_service():
    """Mock audio service"""
    with patch("zikos.api.audio.audio_service") as mock:
        yield mock


class TestAudioAPI:
    """Tests for audio API endpoints"""

    def test_upload_audio_success(self, client, mock_audio_service):
        """Test successful audio upload"""
        mock_audio_service.store_audio = AsyncMock(return_value="test_audio_id")
        mock_audio_service.run_baseline_analysis = AsyncMock(
            return_value={"tempo": {"bpm": 120}, "pitch": {"notes": []}}
        )

        file_content = b"fake audio content"
        files = {"file": ("test.wav", file_content, "audio/wav")}
        data = {"recording_id": "test_recording"}

        response = client.post("/api/audio/upload", files=files, data=data)

        assert response.status_code == 200
        result = response.json()
        assert result["audio_file_id"] == "test_audio_id"
        assert result["recording_id"] == "test_recording"
        assert "analysis" in result

    def test_upload_audio_without_recording_id(self, client, mock_audio_service):
        """Test audio upload without recording ID"""
        mock_audio_service.store_audio = AsyncMock(return_value="test_audio_id")
        mock_audio_service.run_baseline_analysis = AsyncMock(return_value={"tempo": {"bpm": 120}})

        file_content = b"fake audio content"
        files = {"file": ("test.wav", file_content, "audio/wav")}

        response = client.post("/api/audio/upload", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["audio_file_id"] == "test_audio_id"
        assert result.get("recording_id") is None

    def test_upload_audio_error(self, client, mock_audio_service):
        """Test audio upload error handling"""
        mock_audio_service.store_audio = AsyncMock(side_effect=Exception("Storage failed"))

        file_content = b"fake audio content"
        files = {"file": ("test.wav", file_content, "audio/wav")}

        response = client.post("/api/audio/upload", files=files)

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_get_audio_info_success(self, client, mock_audio_service):
        """Test getting audio info successfully"""
        mock_audio_service.get_audio_info = AsyncMock(
            return_value={"duration": 10.5, "sample_rate": 44100, "channels": 2}
        )

        response = client.get("/api/audio/test_audio_id/info")

        assert response.status_code == 200
        result = response.json()
        assert result["duration"] == 10.5
        assert result["sample_rate"] == 44100

    def test_get_audio_info_not_found(self, client, mock_audio_service):
        """Test getting audio info for non-existent file"""
        mock_audio_service.get_audio_info = AsyncMock(
            side_effect=FileNotFoundError("File not found")
        )

        response = client.get("/api/audio/nonexistent/info")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_get_audio_file_success(self, client, mock_audio_service, temp_dir):
        """Test getting audio file successfully"""
        from pathlib import Path

        test_file = temp_dir / "test_audio.wav"
        test_file.write_bytes(b"fake audio content")
        mock_audio_service.get_audio_path = AsyncMock(return_value=test_file)

        response = client.get("/api/audio/test_audio_id")

        assert response.status_code == 200
        assert len(response.content) > 0

    def test_get_audio_file_not_found(self, client, mock_audio_service):
        """Test getting non-existent audio file"""
        mock_audio_service.get_audio_path = AsyncMock(
            side_effect=FileNotFoundError("File not found")
        )

        response = client.get("/api/audio/nonexistent")

        assert response.status_code == 404
        assert "detail" in response.json()
