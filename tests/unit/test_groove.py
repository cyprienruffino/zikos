"""Tests for groove analysis tool"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.audio import AudioAnalysisTools
from zikos.mcp.tools.audio.groove import analyze_groove


@pytest.mark.asyncio
async def test_analyze_groove_success(temp_dir, sample_audio_path):
    """Test successful groove analysis"""
    sample_rate = 22050
    duration = 5.0
    beat_duration = 0.5

    t = np.linspace(0, duration, int(sample_rate * duration))
    y = np.zeros_like(t, dtype=np.float32)

    for beat_time in np.arange(0, duration, beat_duration):
        beat_start = int(beat_time * sample_rate)
        beat_end = min(int((beat_time + 0.1) * sample_rate), len(y))
        if beat_end > beat_start:
            beat_samples = beat_end - beat_start
            beat_t = np.linspace(0, 0.1, beat_samples)
            beat_audio = np.sin(2 * np.pi * 440 * beat_t) * 0.5
            y[beat_start:beat_end] = beat_audio[: beat_end - beat_start]

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    assert "error" not in result
    assert "groove_type" in result
    assert "swing_ratio" in result
    assert "microtiming_pattern" in result
    assert "feel_score" in result
    assert "groove_consistency" in result
    assert result["groove_type"] in ["straight", "swung", "reverse_swing"]
    assert 0.0 <= result["swing_ratio"] <= 2.0
    assert result["microtiming_pattern"] in ["consistent", "variable", "inconsistent"]
    assert 0.0 <= result["feel_score"] <= 1.0
    assert 0.0 <= result["groove_consistency"] <= 1.0


@pytest.mark.asyncio
async def test_analyze_groove_too_short(temp_dir, sample_audio_path):
    """Test groove analysis with too short audio"""
    sample_rate = 22050
    duration = 0.3
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_analyze_groove_insufficient_onsets(temp_dir, sample_audio_path):
    """Test groove analysis with insufficient onsets"""
    sample_rate = 22050
    duration = 1.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "INSUFFICIENT_ONSETS"


@pytest.mark.asyncio
async def test_analyze_groove_via_tools_class(temp_dir, sample_audio_path):
    """Test groove analysis via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 4.0
    beat_duration = 0.5

    t = np.linspace(0, duration, int(sample_rate * duration))
    y = np.zeros_like(t, dtype=np.float32)

    for beat_time in np.arange(0, duration, beat_duration):
        beat_start = int(beat_time * sample_rate)
        beat_end = min(int((beat_time + 0.1) * sample_rate), len(y))
        if beat_end > beat_start:
            beat_samples = beat_end - beat_start
            beat_t = np.linspace(0, 0.1, beat_samples)
            beat_audio = np.sin(2 * np.pi * 440 * beat_t) * 0.5
            y[beat_start:beat_end] = beat_audio[: beat_end - beat_start]

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.analyze_groove(audio_file_id)

    assert "error" not in result
    assert "groove_type" in result
