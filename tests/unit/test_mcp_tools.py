"""Tests for MCP tools"""

from unittest.mock import patch

import pytest

from src.zikos.mcp.tools.audio import AudioAnalysisTools
from src.zikos.mcp.tools.recording import RecordingTools


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
async def test_request_audio_recording():
    """Test audio recording request tool"""
    tools = RecordingTools()

    result = await tools.request_audio_recording("Play C major scale", 60.0)

    assert result["status"] == "recording_requested"
    assert result["prompt"] == "Play C major scale"
    assert result["max_duration"] == 60.0
    assert "recording_id" in result
