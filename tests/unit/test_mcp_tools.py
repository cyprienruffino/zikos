"""Tests for MCP tools"""

from unittest.mock import patch

import pytest

from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.interaction import (
    ChordProgressionTools,
    EarTrainerTools,
    MetronomeTools,
    PracticeTimerTools,
    RecordingTools,
    TempoTrainerTools,
    TunerTools,
)


@pytest.mark.asyncio
async def test_analyze_tempo(temp_dir, sample_audio_path):
    """Test tempo analysis tool with mocked librosa"""
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
@pytest.mark.integration
async def test_analyze_tempo_with_real_audio(temp_dir):
    """Test tempo analysis with real synthesized audio"""
    from pathlib import Path

    from tests.helpers.audio_synthesis import create_test_audio_file
    from zikos.config import settings
    from zikos.mcp.tools.analysis.audio.utils import resolve_audio_path

    # Create synthesized rhythmic audio
    audio_file = temp_dir / "test_rhythm.wav"
    create_test_audio_file(audio_file, audio_type="rhythm", duration=5.0, tempo=120.0)

    # Store in expected location
    import shutil
    import uuid

    audio_file_id = str(uuid.uuid4())
    target_path = temp_dir / f"{audio_file_id}.wav"
    shutil.copy(audio_file, target_path)

    try:
        tools = AudioAnalysisTools()
        result = await tools.analyze_tempo(audio_file_id=audio_file_id)

        assert isinstance(result, dict)
        # Should have BPM or error
        assert "bpm" in result or "error" in result
        if "bpm" in result:
            # BPM should be reasonable (not 0 or negative)
            assert result["bpm"] > 0
            assert result["bpm"] < 300  # Reasonable upper bound
    finally:
        if target_path.exists():
            target_path.unlink()


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
async def test_metronome_call_tool_unknown_tool():
    """Test metronome call_tool with unknown tool"""
    tools = MetronomeTools()

    with pytest.raises(ValueError, match="Unknown tool"):
        await tools.call_tool("unknown_tool", bpm=120)


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


@pytest.mark.asyncio
async def test_tuner_call_tool_unknown_tool():
    """Test tuner call_tool with unknown tool"""
    tools = TunerTools()

    with pytest.raises(ValueError, match="Unknown tool"):
        await tools.call_tool("unknown_tool", reference_frequency=440.0)


@pytest.mark.asyncio
async def test_tempo_trainer_call_tool_unknown_tool():
    """Test tempo trainer call_tool with unknown tool"""
    tools = TempoTrainerTools()

    with pytest.raises(ValueError, match="Unknown tool"):
        await tools.call_tool("unknown_tool", start_bpm=60)


@pytest.mark.asyncio
async def test_chord_progression_call_tool_unknown_tool():
    """Test chord progression call_tool with unknown tool"""
    tools = ChordProgressionTools()

    with pytest.raises(ValueError, match="Unknown tool"):
        await tools.call_tool("unknown_tool", chords=["C"])


@pytest.mark.asyncio
async def test_ear_trainer_call_tool_unknown_tool():
    """Test ear trainer call_tool with unknown tool"""
    tools = EarTrainerTools()

    with pytest.raises(ValueError, match="Unknown tool"):
        await tools.call_tool("unknown_tool", mode="intervals")


@pytest.mark.asyncio
async def test_practice_timer_call_tool_unknown_tool():
    """Test practice timer call_tool with unknown tool"""
    tools = PracticeTimerTools()

    with pytest.raises(ValueError, match="Unknown tool"):
        await tools.call_tool("unknown_tool", duration_minutes=30)
