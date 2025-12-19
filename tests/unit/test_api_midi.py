"""Unit tests for MIDI API endpoints"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from zikos.api.midi import router
from zikos.main import app

app.include_router(router, prefix="/api/midi")


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_midi_service():
    """Mock MIDI service"""
    with patch("zikos.api.midi.midi_service") as mock:
        yield mock


class TestMidiAPI:
    """Tests for MIDI API endpoints"""

    def test_validate_midi_success(self, client, mock_midi_service):
        """Test successful MIDI validation"""
        mock_midi_service.validate_midi = AsyncMock(
            return_value={"valid": True, "midi_file_id": "test_midi", "errors": [], "warnings": []}
        )

        response = client.post("/api/midi/validate", json={"midi_text": "[MIDI]\n[/MIDI]"})

        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is True
        assert "midi_file_id" in result

    def test_validate_midi_error(self, client, mock_midi_service):
        """Test MIDI validation error handling"""
        mock_midi_service.validate_midi = AsyncMock(side_effect=ValueError("Invalid MIDI"))

        response = client.post("/api/midi/validate", json={"midi_text": "invalid"})

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_synthesize_midi_success(self, client, mock_midi_service):
        """Test successful MIDI synthesis"""
        mock_midi_service.synthesize = AsyncMock(return_value="test_audio_id")

        response = client.post("/api/midi/test_midi/synthesize?instrument=piano")

        assert response.status_code == 200
        result = response.json()
        assert result["audio_file_id"] == "test_audio_id"

    def test_synthesize_midi_error(self, client, mock_midi_service):
        """Test MIDI synthesis error handling"""
        mock_midi_service.synthesize = AsyncMock(side_effect=Exception("Synthesis failed"))

        response = client.post("/api/midi/test_midi/synthesize?instrument=piano")

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_render_notation_success(self, client, mock_midi_service):
        """Test successful notation rendering"""
        mock_midi_service.render_notation = AsyncMock(
            return_value={"midi_file_id": "test_midi", "format": "both", "file_path": "test.xml"}
        )

        response = client.post("/api/midi/test_midi/render?format=both")

        assert response.status_code == 200
        result = response.json()
        assert result["midi_file_id"] == "test_midi"
        assert result["format"] == "both"

    def test_render_notation_error(self, client, mock_midi_service):
        """Test notation rendering error handling"""
        mock_midi_service.render_notation = AsyncMock(side_effect=Exception("Render failed"))

        response = client.post("/api/midi/test_midi/render?format=both")

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_get_midi_file_success(self, client, mock_midi_service, temp_dir):
        """Test getting MIDI file successfully"""
        from pathlib import Path

        test_file = temp_dir / "test.mid"
        test_file.write_bytes(b"fake midi content")
        mock_midi_service.get_midi_path = AsyncMock(return_value=test_file)

        response = client.get("/api/midi/test_midi")

        assert response.status_code == 200
        assert "audio/midi" in response.headers["content-type"]
        assert len(response.content) > 0

    def test_get_midi_file_not_found(self, client, mock_midi_service):
        """Test getting non-existent MIDI file"""
        mock_midi_service.get_midi_path = AsyncMock(side_effect=FileNotFoundError("File not found"))

        response = client.get("/api/midi/nonexistent")

        assert response.status_code == 404
        assert "detail" in response.json()
