"""REAL integration tests for audio upload and processing

These tests use REAL audio files and REAL analysis - no mocks.
Run with: pytest tests/integration/test_audio_upload_full.py -v
"""

import json
import math
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zikos.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def create_test_audio_file(temp_dir: Path, duration: float = 1.0, frequency: float = 440.0) -> Path:
    """Create a real WAV file for testing"""
    sample_rate = 44100
    audio_data = b""
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        sample = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * t))
        audio_data += sample.to_bytes(2, byteorder="little", signed=True)

    test_wav = temp_dir / "test_audio.wav"
    with wave.open(str(test_wav), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)

    return test_wav


class TestAudioUploadFullFlow:
    """REAL integration tests for complete audio upload flow"""

    def test_upload_and_analyze_real_audio(self, client, temp_dir):
        """Test uploading real audio and getting analysis"""
        audio_file = create_test_audio_file(temp_dir, duration=1.0, frequency=440.0)

        with open(audio_file, "rb") as f:
            response = client.post(
                "/api/audio/upload",
                files={"file": ("test.wav", f.read(), "audio/wav")},
                data={"recording_id": "test_recording"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "audio_file_id" in data
        assert "analysis" in data
        assert "tempo" in data["analysis"]
        assert "pitch" in data["analysis"]
        assert "rhythm" in data["analysis"]

    def test_websocket_audio_ready_with_real_audio(self, client, temp_dir):
        """Test complete WebSocket flow with real audio upload and analysis"""
        # First upload real audio
        audio_file = create_test_audio_file(temp_dir, duration=1.0, frequency=440.0)

        with open(audio_file, "rb") as f:
            upload_response = client.post(
                "/api/audio/upload",
                files={"file": ("test.wav", f.read(), "audio/wav")},
                data={"recording_id": "test_recording"},
            )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        audio_file_id = upload_data["audio_file_id"]

        # Now test WebSocket audio_ready
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "audio_ready",
                    "audio_file_id": audio_file_id,
                    "recording_id": "test_recording",
                    "session_id": "test_session",
                }
            )

            # Should get a response (might be error if LLM not available, but should not crash)
            response = websocket.receive_json()

            assert "type" in response
            # Should be either "response" or "error" - both are valid
            assert response["type"] in ["response", "error"]

            if response["type"] == "error":
                # If error, check it's a meaningful error, not a crash
                assert "message" in response
                error_msg = response["message"].lower()
                # Should mention LLM or model, not be a generic crash
                assert any(keyword in error_msg for keyword in ["llm", "model", "available"])

    def test_websocket_audio_ready_error_handling(self, client):
        """Test error handling when audio file doesn't exist"""
        with client.websocket_connect("/api/chat/ws") as websocket:
            websocket.send_json(
                {
                    "type": "audio_ready",
                    "audio_file_id": "nonexistent_file_id_12345",
                    "recording_id": "test_recording",
                    "session_id": "test_session",
                }
            )

            # Should get an error response, not crash
            response = websocket.receive_json()

            assert "type" in response
            assert response["type"] in ["response", "error"]
            # Should handle the error gracefully
