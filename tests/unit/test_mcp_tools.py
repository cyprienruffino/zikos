"""Tests for MCP tools"""

from unittest.mock import patch

import pytest

from zikos.mcp.tools.audio import AudioAnalysisTools
from zikos.mcp.tools.chord_progression import ChordProgressionTools
from zikos.mcp.tools.ear_trainer import EarTrainerTools
from zikos.mcp.tools.metronome import MetronomeTools
from zikos.mcp.tools.practice_timer import PracticeTimerTools
from zikos.mcp.tools.recording import RecordingTools
from zikos.mcp.tools.tempo_trainer import TempoTrainerTools
from zikos.mcp.tools.tuner import TunerTools


@pytest.mark.asyncio
async def test_analyze_tempo(temp_dir, sample_audio_path):
    """Test tempo analysis tool"""
    # Create dummy audio file
    sample_audio_path.touch()

    tools = AudioAnalysisTools()

    with patch("librosa.load") as mock_load:
        # Generate 2 seconds of audio at 22050 Hz (enough to pass duration check)
        mock_load.return_value = ([0.0] * 44100, 22050)
        with patch("librosa.beat.beat_track") as mock_beat:
            mock_beat.return_value = (120.0, [0, 5512, 11025])

            result = await tools.analyze_tempo(audio_path=str(sample_audio_path))

            assert "bpm" in result
            assert result["bpm"] == 120.0
            assert "confidence" in result


@pytest.mark.asyncio
async def test_create_metronome():
    """Test metronome creation tool"""
    tools = MetronomeTools()

    result = await tools.create_metronome(120, "4/4", "Practice with this tempo")

    assert result["status"] == "metronome_created"
    assert result["bpm"] == 120
    assert result["time_signature"] == "4/4"
    assert result["description"] == "Practice with this tempo"
    assert "metronome_id" in result

    result_no_desc = await tools.create_metronome(90, "3/4", None)

    assert result_no_desc["status"] == "metronome_created"
    assert result_no_desc["bpm"] == 90
    assert result_no_desc["time_signature"] == "3/4"
    assert result_no_desc["description"] is None


@pytest.mark.asyncio
async def test_create_tuner():
    """Test tuner creation tool"""
    tools = TunerTools()

    result = await tools.create_tuner(440.0, "A", 4, "Tune your instrument")

    assert result["status"] == "tuner_created"
    assert result["reference_frequency"] == 440.0
    assert result["note"] == "A"
    assert result["octave"] == 4
    assert result["description"] == "Tune your instrument"
    assert "tuner_id" in result


@pytest.mark.asyncio
async def test_create_chord_progression():
    """Test chord progression creation tool"""
    tools = ChordProgressionTools()

    result = await tools.create_chord_progression(
        ["C", "G", "Am", "F"], 120, "4/4", 1, "piano", "Practice with this progression"
    )

    assert result["status"] == "chord_progression_created"
    assert result["chords"] == ["C", "G", "Am", "F"]
    assert result["tempo"] == 120
    assert result["time_signature"] == "4/4"
    assert result["chords_per_bar"] == 1
    assert result["instrument"] == "piano"
    assert result["description"] == "Practice with this progression"
    assert "progression_id" in result


@pytest.mark.asyncio
async def test_create_tempo_trainer():
    """Test tempo trainer creation tool"""
    tools = TempoTrainerTools()

    result = await tools.create_tempo_trainer(60, 120, 5.0, "4/4", "linear", "Build up speed")

    assert result["status"] == "tempo_trainer_created"
    assert result["start_bpm"] == 60
    assert result["end_bpm"] == 120
    assert result["duration_minutes"] == 5.0
    assert result["time_signature"] == "4/4"
    assert result["ramp_type"] == "linear"
    assert result["description"] == "Build up speed"
    assert "trainer_id" in result


@pytest.mark.asyncio
async def test_create_ear_trainer():
    """Test ear trainer creation tool"""
    tools = EarTrainerTools()

    result = await tools.create_ear_trainer(
        "intervals", "medium", "C", "Practice interval recognition"
    )

    assert result["status"] == "ear_trainer_created"
    assert result["mode"] == "intervals"
    assert result["difficulty"] == "medium"
    assert result["root_note"] == "C"
    assert result["description"] == "Practice interval recognition"
    assert "trainer_id" in result


@pytest.mark.asyncio
async def test_create_practice_timer():
    """Test practice timer creation tool"""
    tools = PracticeTimerTools()

    result = await tools.create_practice_timer(30, "Work on scales", 25, "Practice for 30 minutes")

    assert result["status"] == "practice_timer_created"
    assert result["duration_minutes"] == 30
    assert result["goal"] == "Work on scales"
    assert result["break_interval_minutes"] == 25
    assert result["description"] == "Practice for 30 minutes"
    assert "timer_id" in result


@pytest.mark.asyncio
async def test_request_audio_recording():
    """Test audio recording request tool"""
    tools = RecordingTools()

    result = await tools.request_audio_recording("Play C major scale", 60.0)

    assert result["status"] == "recording_requested"
    assert result["prompt"] == "Play C major scale"
    assert result["max_duration"] == 60.0
    assert "recording_id" in result
