"""Integration tests for MIDI API"""

import pytest
from fastapi.testclient import TestClient

from zikos.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestMidiAPI:
    """Tests for MIDI API endpoints"""

    def test_validate_midi(self, client, temp_dir):
        """Test MIDI validation with real implementation"""
        midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        response = client.post("/api/midi/validate", json={"midi_text": midi_text})

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert data["valid"] is True
        assert "midi_file_id" in data
        assert data["midi_file_id"] != ""

    def test_validate_midi_invalid(self, client):
        """Test MIDI validation with invalid input"""
        response = client.post("/api/midi/validate", json={"midi_text": "invalid MIDI"})

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert data["valid"] is False
        assert len(data.get("errors", [])) > 0

    def test_validate_midi_error_handling(self, client):
        """Test MIDI validation error handling"""
        response = client.post("/api/midi/validate", json={"midi_text": ""})

        assert response.status_code in [200, 400]

    def test_synthesize_midi(self, client, temp_dir):
        """Test MIDI synthesis with real implementation"""
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_api_synth"
            midi_path = Path(settings.midi_storage_path) / f"{midi_file_id}.mid"
            midi_path.parent.mkdir(parents=True, exist_ok=True)

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_text_to_file(midi_text, midi_path)

            try:
                response = client.post(f"/api/midi/{midi_file_id}/synthesize?instrument=piano")

                if response.status_code == 200:
                    data = response.json()
                    assert "audio_file_id" in data
                    assert data["audio_file_id"] != ""
                elif response.status_code == 500:
                    error_detail = response.json().get("detail", "")
                    if "SoundFont" in error_detail or "fluidsynth" in error_detail.lower():
                        pytest.skip(f"Skipping synthesis test: {error_detail}")
                    raise AssertionError(f"Unexpected error: {error_detail}")
            except Exception as e:
                if "SoundFont" in str(e) or "fluidsynth" in str(e).lower():
                    pytest.skip(f"Skipping synthesis test: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")

    def test_render_notation(self, client, temp_dir):
        """Test notation rendering with real implementation"""
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_api_notation"
            midi_path = Path(settings.midi_storage_path) / f"{midi_file_id}.mid"
            midi_path.parent.mkdir(parents=True, exist_ok=True)

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_text_to_file(midi_text, midi_path)

            try:
                response = client.post(f"/api/midi/{midi_file_id}/render?format=both")

                assert response.status_code == 200
                data = response.json()
                assert "midi_file_id" in data
                assert data["midi_file_id"] == midi_file_id
                assert "format" in data
            except Exception as e:
                if "lilypond" in str(e).lower() or "musescore" in str(e).lower():
                    pytest.skip(f"Skipping notation test: {e}")
                raise
        except ImportError:
            pytest.skip("music21 not available")
