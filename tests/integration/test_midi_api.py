"""Integration tests for MIDI API"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestMidiAPI:
    """Tests for MIDI API endpoints"""

    def test_validate_midi(self, client):
        """Test MIDI validation"""
        with patch("src.zikos.api.midi.midi_service") as mock_service:
            mock_service.validate_midi = AsyncMock(
                return_value={
                    "valid": True,
                    "midi_file_id": "test",
                    "errors": [],
                }
            )

            response = client.post("/api/midi/validate?midi_text=[MIDI]C4[/MIDI]")

            assert response.status_code == 200
            data = response.json()
            assert "valid" in data

    def test_validate_midi_error(self, client):
        """Test MIDI validation with error"""
        with patch("src.zikos.api.midi.midi_service") as mock_service:
            mock_service.validate_midi = AsyncMock(side_effect=Exception("Validation failed"))

            response = client.post("/api/midi/validate?midi_text=invalid")

            assert response.status_code == 400

    def test_synthesize_midi(self, client):
        """Test MIDI synthesis"""
        with patch("src.zikos.api.midi.midi_service") as mock_service:
            mock_service.synthesize = AsyncMock(return_value="test_audio_id")

            response = client.post("/api/midi/test_midi/synthesize?instrument=piano")

            assert response.status_code == 200
            data = response.json()
            assert "audio_file_id" in data

    def test_render_notation(self, client):
        """Test notation rendering"""
        with patch("src.zikos.api.midi.midi_service") as mock_service:
            mock_service.render_notation = AsyncMock(
                return_value={
                    "sheet_music_url": "/notation/sheet.png",
                }
            )

            response = client.post("/api/midi/test_midi/render?format=both")

            assert response.status_code == 200
            data = response.json()
            assert "sheet_music_url" in data
