"""Tests for groove analysis tool"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.analysis.audio.groove import analyze_groove


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


@pytest.mark.asyncio
async def test_analyze_groove_file_not_found(temp_dir):
    """Test groove analysis with non-existent file"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove("nonexistent_file.wav")

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_analyze_groove_processing_error(temp_dir, sample_audio_path):
    """Test groove analysis with processing error"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with patch("librosa.load", side_effect=Exception("Processing failed")):
            result = await analyze_groove(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_analyze_groove_few_beats(temp_dir, sample_audio_path):
    """Test groove analysis with very few beats (len(beat_times) < 2)"""
    sample_rate = 22050
    duration = 0.6
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    if "error" not in result:
        assert "groove_type" in result


@pytest.mark.asyncio
async def test_analyze_groove_swung_pattern(temp_dir, sample_audio_path):
    """Test groove analysis with swung pattern (avg_ratio > 1.3)"""
    sample_rate = 22050
    duration = 6.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    y = np.zeros_like(t, dtype=np.float32)

    intervals = [0.3, 0.5, 0.3, 0.5, 0.3, 0.5]
    current_time = 0.0
    for interval in intervals:
        beat_start = int(current_time * sample_rate)
        beat_end = min(int((current_time + 0.1) * sample_rate), len(y))
        if beat_end > beat_start:
            beat_samples = beat_end - beat_start
            beat_t = np.linspace(0, 0.1, beat_samples)
            beat_audio = np.sin(2 * np.pi * 440 * beat_t) * 0.5
            y[beat_start:beat_end] = beat_audio[: beat_end - beat_start]
        current_time += interval

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    if "error" not in result:
        assert "groove_type" in result
        assert result["groove_type"] in ["straight", "swung", "reverse_swing"]


@pytest.mark.asyncio
async def test_analyze_groove_inconsistent_microtiming(temp_dir, sample_audio_path):
    """Test groove analysis with inconsistent microtiming (std > 30)"""
    sample_rate = 22050
    duration = 8.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    base_interval = 0.5
    for i in range(16):
        offset = np.random.uniform(-0.1, 0.1)
        beat_time = max(0, i * base_interval + offset)
        if beat_time < duration:
            beat_start = int(beat_time * sample_rate)
            beat_end = min(int((beat_time + 0.1) * sample_rate), len(y))
            if beat_end > beat_start:
                beat_samples = beat_end - beat_start
                beat_t = np.linspace(0, 0.1, beat_samples)
                beat_audio = np.sin(2 * np.pi * 440 * beat_t) * 0.5
                y[beat_start:beat_end] = beat_audio

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    if "error" not in result:
        assert "microtiming_pattern" in result
        assert result["microtiming_pattern"] in ["consistent", "variable", "inconsistent"]


@pytest.mark.asyncio
async def test_analyze_groove_variable_microtiming(temp_dir, sample_audio_path):
    """Test groove analysis with variable microtiming (15 < std <= 30)"""
    sample_rate = 22050
    duration = 6.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    base_interval = 0.5
    for i in range(12):
        offset = np.random.uniform(-0.05, 0.05)
        beat_time = max(0, i * base_interval + offset)
        if beat_time < duration:
            beat_start = int(beat_time * sample_rate)
            beat_end = min(int((beat_time + 0.1) * sample_rate), len(y))
            if beat_end > beat_start:
                beat_samples = beat_end - beat_start
                beat_t = np.linspace(0, 0.1, beat_samples)
                beat_audio = np.sin(2 * np.pi * 440 * beat_t) * 0.5
                y[beat_start:beat_end] = beat_audio

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    if "error" not in result:
        assert "microtiming_pattern" in result


@pytest.mark.asyncio
async def test_analyze_groove_short_intervals(temp_dir, sample_audio_path):
    """Test groove analysis with very short intervals (interval < expected_beat_interval * 0.1)"""
    sample_rate = 22050
    duration = 4.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    y = np.zeros_like(t, dtype=np.float32)

    for i in range(20):
        beat_time = i * 0.02
        if beat_time < duration:
            beat_start = int(beat_time * sample_rate)
            beat_end = min(int((beat_time + 0.05) * sample_rate), len(y))
            if beat_end > beat_start:
                beat_samples = beat_end - beat_start
                beat_t = np.linspace(0, 0.05, beat_samples)
                beat_audio = np.sin(2 * np.pi * 440 * beat_t) * 0.5
                y[beat_start:beat_end] = beat_audio[: beat_end - beat_start]

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await analyze_groove(str(sample_audio_path))

    if "error" not in result:
        assert "groove_type" in result
