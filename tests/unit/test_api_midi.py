"""Unit tests for MIDI API endpoints"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from zikos.api.midi import router
from zikos.main import app

MIDI_ID = "22222222-2222-4222-8222-222222222222"

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

        response = client.post(f"/api/midi/{MIDI_ID}/synthesize?instrument=piano")

        assert response.status_code == 200
        result = response.json()
        assert result["audio_file_id"] == "test_audio_id"

    def test_synthesize_midi_error(self, client, mock_midi_service):
        """Test MIDI synthesis error handling"""
        mock_midi_service.synthesize = AsyncMock(side_effect=Exception("Synthesis failed"))

        response = client.post(f"/api/midi/{MIDI_ID}/synthesize?instrument=piano")

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_render_notation_success(self, client, mock_midi_service):
        """Test successful notation rendering"""
        mock_midi_service.render_notation = AsyncMock(
            return_value={"midi_file_id": "test_midi", "format": "both", "file_path": "test.xml"}
        )

        response = client.post(f"/api/midi/{MIDI_ID}/render?format=both")

        assert response.status_code == 200
        result = response.json()
        assert result["midi_file_id"] == "test_midi"
        assert result["format"] == "both"

    def test_render_notation_error(self, client, mock_midi_service):
        """Test notation rendering error handling"""
        mock_midi_service.render_notation = AsyncMock(side_effect=Exception("Render failed"))

        response = client.post(f"/api/midi/{MIDI_ID}/render?format=both")

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_get_midi_file_success(self, client, mock_midi_service, temp_dir):
        """Test getting MIDI file successfully"""
        from pathlib import Path

        test_file = temp_dir / "test.mid"
        test_file.write_bytes(b"fake midi content")
        mock_midi_service.get_midi_path = AsyncMock(return_value=test_file)

        response = client.get(f"/api/midi/{MIDI_ID}")

        assert response.status_code == 200
        assert "audio/midi" in response.headers["content-type"]
        assert len(response.content) > 0

    def test_get_midi_file_not_found(self, client, mock_midi_service):
        """Test getting non-existent MIDI file"""
        mock_midi_service.get_midi_path = AsyncMock(side_effect=FileNotFoundError("File not found"))

        response = client.get(f"/api/midi/{MIDI_ID}")

        assert response.status_code == 404
        assert "detail" in response.json()


class TestMidiIdValidation:
    """Path IDs must be UUIDs before touching the filesystem"""

    def test_get_midi_rejects_traversal_id(self, client, mock_midi_service):
        response = client.get("/api/midi/..%5C..%5Cwindows")
        assert response.status_code == 400
        mock_midi_service.get_midi_path.assert_not_called()

    def test_get_midi_rejects_non_uuid_id(self, client, mock_midi_service):
        response = client.get("/api/midi/not-a-uuid")
        assert response.status_code == 400
        mock_midi_service.get_midi_path.assert_not_called()

    def test_synthesize_rejects_non_uuid_id(self, client, mock_midi_service):
        response = client.post("/api/midi/evil.mid/synthesize?instrument=piano")
        assert response.status_code == 400
        mock_midi_service.synthesize.assert_not_called()

    def test_render_rejects_non_uuid_id(self, client, mock_midi_service):
        response = client.post("/api/midi/evil/render?format=both")
        assert response.status_code == 400
        mock_midi_service.render_notation.assert_not_called()


class TestMidiErrorHandling:
    """Error mapping: 404 for missing files, 400 for bad input, generic 500"""

    def test_unexpected_error_does_not_leak_details(self, client, mock_midi_service):
        mock_midi_service.synthesize = AsyncMock(
            side_effect=Exception("secret internal path /srv/keys")
        )
        response = client.post(f"/api/midi/{MIDI_ID}/synthesize?instrument=piano")
        assert response.status_code == 500
        assert "secret internal path" not in response.json()["detail"]

    def test_missing_midi_file_maps_to_404(self, client, mock_midi_service):
        mock_midi_service.synthesize = AsyncMock(side_effect=FileNotFoundError("no such MIDI"))
        response = client.post(f"/api/midi/{MIDI_ID}/synthesize?instrument=piano")
        assert response.status_code == 404

    def test_value_error_maps_to_400(self, client, mock_midi_service):
        mock_midi_service.render_notation = AsyncMock(side_effect=ValueError("bad format"))
        response = client.post(f"/api/midi/{MIDI_ID}/render?format=bogus")
        assert response.status_code == 400
