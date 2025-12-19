"""Tests for MIDI parser"""

from pathlib import Path

import pytest

from zikos.mcp.tools.midi_parser import (
    MidiParseError,
    create_music21_stream,
    midi_text_to_file,
    parse_midi_text,
    parse_note_line,
)


class TestParseNoteLine:
    """Tests for parse_note_line"""

    def test_parse_simple_note(self):
        """Test parsing a simple note"""
        result = parse_note_line("C4")
        assert result is not None
        assert result["note"] == "C4"
        assert result["velocity"] == 60
        assert result["duration"] == 0.5

    def test_parse_note_with_velocity(self):
        """Test parsing note with velocity"""
        result = parse_note_line("C4 velocity=80")
        assert result is not None
        assert result["note"] == "C4"
        assert result["velocity"] == 80
        assert result["duration"] == 0.5

    def test_parse_note_with_duration(self):
        """Test parsing note with duration"""
        result = parse_note_line("C4 duration=1.0")
        assert result is not None
        assert result["note"] == "C4"
        assert result["velocity"] == 60
        assert result["duration"] == 1.0

    def test_parse_note_with_both(self):
        """Test parsing note with both velocity and duration"""
        result = parse_note_line("C4 velocity=90 duration=0.75")
        assert result is not None
        assert result["note"] == "C4"
        assert result["velocity"] == 90
        assert result["duration"] == 0.75

    def test_parse_empty_line(self):
        """Test parsing empty line"""
        result = parse_note_line("")
        assert result is None

    def test_parse_invalid_velocity(self):
        """Test parsing with invalid velocity"""
        result = parse_note_line("C4 velocity=invalid")
        assert result is not None
        assert result["velocity"] == 60

    def test_parse_invalid_duration(self):
        """Test parsing with invalid duration"""
        result = parse_note_line("C4 duration=invalid")
        assert result is not None
        assert result["duration"] == 0.5


class TestParseMidiText:
    """Tests for parse_midi_text"""

    def test_parse_simple_midi(self):
        """Test parsing simple MIDI text"""
        midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
[/MIDI]
"""
        result = parse_midi_text(midi_text)
        assert "metadata" in result
        assert "tracks" in result
        assert result["metadata"]["tempo"] == 120
        assert result["metadata"]["time_signature"] == "4/4"
        assert result["metadata"]["key"] == "C major"
        assert len(result["tracks"]) == 1
        assert len(result["tracks"][0]["notes"]) == 2

    def test_parse_midi_with_track_name(self):
        """Test parsing MIDI with named track"""
        midi_text = """
[MIDI]
Tempo: 120
Track 1 (Melody):
  C4 velocity=70 duration=0.5
[/MIDI]
"""
        result = parse_midi_text(midi_text)
        assert len(result["tracks"]) == 1
        assert result["tracks"][0]["name"] == "Melody"
        assert result["tracks"][0]["number"] == 1

    def test_parse_midi_multiple_tracks(self):
        """Test parsing MIDI with multiple tracks"""
        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
Track 2:
  E4 velocity=50 duration=1.0
[/MIDI]
"""
        result = parse_midi_text(midi_text)
        assert len(result["tracks"]) == 2
        assert len(result["tracks"][0]["notes"]) == 1
        assert len(result["tracks"][1]["notes"]) == 1

    def test_parse_midi_default_metadata(self):
        """Test parsing MIDI with default metadata"""
        midi_text = """
[MIDI]
Track 1:
  C4
[/MIDI]
"""
        result = parse_midi_text(midi_text)
        assert result["metadata"]["tempo"] == 120
        assert result["metadata"]["time_signature"] == "4/4"
        assert result["metadata"]["key"] == "C major"

    def test_parse_midi_no_block(self):
        """Test parsing MIDI without [MIDI] block"""
        with pytest.raises(MidiParseError, match="No \\[MIDI\\]"):
            parse_midi_text("Just some text")

    def test_parse_midi_no_tracks(self):
        """Test parsing MIDI without tracks"""
        midi_text = """
[MIDI]
Tempo: 120
[/MIDI]
"""
        with pytest.raises(MidiParseError, match="No tracks found"):
            parse_midi_text(midi_text)

    def test_parse_midi_invalid_tempo(self):
        """Test parsing MIDI with invalid tempo"""
        midi_text = """
[MIDI]
Tempo: invalid
Track 1:
  C4
[/MIDI]
"""
        with pytest.raises(MidiParseError, match="Invalid tempo"):
            parse_midi_text(midi_text)


class TestCreateMusic21Stream:
    """Tests for create_music21_stream"""

    @pytest.mark.asyncio
    async def test_create_stream_simple(self):
        """Test creating music21 stream from simple parsed data"""
        try:
            parsed_data = {
                "metadata": {"tempo": 120, "time_signature": "4/4", "key": "C major"},
                "tracks": [
                    {
                        "number": 1,
                        "name": None,
                        "notes": [
                            {"note": "C4", "velocity": 60, "duration": 0.5},
                            {"note": "D4", "velocity": 60, "duration": 0.5},
                        ],
                    }
                ],
            }
            score = create_music21_stream(parsed_data)
            assert score is not None
            assert len(score.parts) == 1
            assert len(score.parts[0].notes) == 2
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_create_stream_invalid_note(self):
        """Test creating stream with invalid note"""
        try:
            parsed_data = {
                "metadata": {"tempo": 120, "time_signature": "4/4", "key": "C major"},
                "tracks": [
                    {
                        "number": 1,
                        "name": None,
                        "notes": [{"note": "INVALID", "velocity": 60, "duration": 0.5}],
                    }
                ],
            }
            with pytest.raises(MidiParseError, match="Invalid note"):
                create_music21_stream(parsed_data)
        except ImportError:
            pytest.skip("music21 not available")


class TestMidiTextToFile:
    """Tests for midi_text_to_file"""

    @pytest.mark.asyncio
    async def test_midi_text_to_file(self, temp_dir):
        """Test converting MIDI text to file"""
        try:
            midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
  D4 velocity=60 duration=0.5
  E4 velocity=60 duration=0.5
[/MIDI]
"""
            output_path = temp_dir / "test.mid"
            midi_text_to_file(midi_text, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_text_to_file_invalid(self, temp_dir):
        """Test converting invalid MIDI text to file"""
        try:
            output_path = temp_dir / "test.mid"
            with pytest.raises(MidiParseError):
                midi_text_to_file("Invalid MIDI", output_path)
        except ImportError:
            pytest.skip("music21 not available")
