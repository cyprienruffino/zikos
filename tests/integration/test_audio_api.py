"""Integration tests for audio API"""

import pytest
from fastapi.testclient import TestClient

from zikos.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestAudioAPI:
    """Tests for audio API endpoints"""

    def test_upload_audio(self, client, temp_dir):
        """Test uploading audio file with real implementation"""
        import math
        import wave
        from pathlib import Path

        sample_rate = 44100
        duration = 0.1
        frequency = 440.0

        audio_data = b""
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
            audio_data += sample.to_bytes(2, byteorder="little", signed=True)

        test_wav = temp_dir / "test_upload.wav"
        with wave.open(str(test_wav), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        with open(test_wav, "rb") as f:
            response = client.post(
                "/api/audio/upload",
                files={"file": ("test.wav", f.read(), "audio/wav")},
                data={"recording_id": "test_recording"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "audio_file_id" in data
        assert data["audio_file_id"] != ""
        assert "recording_id" in data
        assert data.get("recording_id") == "test_recording" or data.get("recording_id") is None
        assert "analysis" in data
        assert "tempo" in data["analysis"]
        assert "pitch" in data["analysis"]
        assert "rhythm" in data["analysis"]

    def test_upload_audio_without_recording_id(self, client, temp_dir):
        """Test uploading audio without recording ID"""
        import math
        import wave
        from pathlib import Path

        sample_rate = 44100
        duration = 0.1
        frequency = 440.0

        audio_data = b""
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
            audio_data += sample.to_bytes(2, byteorder="little", signed=True)

        test_wav = temp_dir / "test_upload2.wav"
        with wave.open(str(test_wav), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        with open(test_wav, "rb") as f:
            response = client.post(
                "/api/audio/upload",
                files={"file": ("test.wav", f.read(), "audio/wav")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "audio_file_id" in data

    def test_get_audio_info(self, client, storage_paths):
        """Test getting audio info with real implementation"""
        import math
        import uuid
        import wave
        from pathlib import Path

        audio_file_id = str(uuid.uuid4())
        audio_path = storage_paths / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        sample_rate = 44100
        duration = 0.1
        frequency = 440.0

        audio_data = b""
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
            audio_data += sample.to_bytes(2, byteorder="little", signed=True)

        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        response = client.get(f"/api/audio/{audio_file_id}/info")

        assert response.status_code == 200
        data = response.json()
        assert "duration" in data
        assert "sample_rate" in data

    def test_get_audio_info_not_found(self, client):
        """Test getting audio info for non-existent file"""
        response = client.get("/api/audio/nonexistent_audio_id_12345/info")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] is True
        assert data["error_type"] == "FILE_NOT_FOUND"

    def test_get_audio_file(self, client, storage_paths):
        """Test getting audio file with real implementation"""
        import math
        import uuid
        import wave
        from pathlib import Path

        audio_file_id = str(uuid.uuid4())
        audio_path = storage_paths / f"{audio_file_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        sample_rate = 44100
        duration = 0.1
        frequency = 440.0

        audio_data = b""
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
            audio_data += sample.to_bytes(2, byteorder="little", signed=True)

        with wave.open(str(audio_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        response = client.get(f"/api/audio/{audio_file_id}")

        assert response.status_code == 200
        assert (
            "audio" in response.headers["content-type"]
            or "application" in response.headers["content-type"]
        )
        assert len(response.content) > 0

    def test_get_audio_file_not_found(self, client):
        """Test getting non-existent audio file"""
        response = client.get("/api/audio/nonexistent_audio_id")

        assert response.status_code == 404
