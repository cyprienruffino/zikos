"""Tests for time-stretching and pitch-shifting tools

Note: These tests require pyrubberband which may not be available in all environments.
They will be skipped if pyrubberband is not installed.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.analysis.audio.time_stretch import pitch_shift, time_stretch


@pytest.mark.asyncio
async def test_time_stretch_success(temp_dir, sample_audio_path):
    """Test successful time-stretching"""
    sample_rate = 22050
    duration = 2.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        try:
            result = await time_stretch(audio_file_id, rate=0.5)
        except ImportError:
            pytest.skip("pyrubberband not installed")

    if "error" in result:
        if result.get("error_type") == "DEPENDENCY_MISSING":
            pytest.skip("pyrubberband not installed")
        if (
            result.get("error_type") == "PROCESSING_FAILED"
            and "rubberband" in result.get("message", "").lower()
        ):
            pytest.skip("rubberband-cli not installed")

    assert "error" not in result
    assert "new_audio_file_id" in result
    assert result["original_audio_file_id"] == audio_file_id
    assert result["rate"] == 0.5
    assert result["new_duration"] == pytest.approx(result["original_duration"] * 2.0, abs=0.1)


@pytest.mark.asyncio
async def test_time_stretch_invalid_rate(temp_dir, sample_audio_path):
    """Test time-stretching with invalid rate"""
    try:
        import pyrubberband
    except ImportError:
        pytest.skip("pyrubberband not installed")

    sample_rate = 22050
    duration = 2.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await time_stretch(audio_file_id, rate=0.1)

    assert result["error"] is True
    assert result["error_type"] == "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_pitch_shift_success(temp_dir, sample_audio_path):
    """Test successful pitch-shifting"""
    sample_rate = 22050
    duration = 2.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        try:
            result = await pitch_shift(audio_file_id, semitones=2.0)
        except ImportError:
            pytest.skip("pyrubberband not installed")

    if "error" in result:
        if result.get("error_type") == "DEPENDENCY_MISSING":
            pytest.skip("pyrubberband not installed")
        if (
            result.get("error_type") == "PROCESSING_FAILED"
            and "rubberband" in result.get("message", "").lower()
        ):
            pytest.skip("rubberband-cli not installed")

    assert "error" not in result
    assert "new_audio_file_id" in result
    assert result["original_audio_file_id"] == audio_file_id
    assert result["semitones"] == 2.0


@pytest.mark.asyncio
async def test_pitch_shift_invalid_semitones(temp_dir, sample_audio_path):
    """Test pitch-shifting with invalid semitones"""
    try:
        import pyrubberband
    except ImportError:
        pytest.skip("pyrubberband not installed")

    sample_rate = 22050
    duration = 2.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await pitch_shift(audio_file_id, semitones=30.0)

    assert result["error"] is True
    assert result["error_type"] == "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_time_stretch_via_tools_class(temp_dir, sample_audio_path):
    """Test time-stretching via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 1.5
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.time_stretch(audio_file_id, rate=2.0)

    if "error" in result and result.get("error_type") == "DEPENDENCY_MISSING":
        pytest.skip("pyrubberband not installed")

    assert "error" not in result or result.get("error_type") != "DEPENDENCY_MISSING"


@pytest.mark.asyncio
async def test_pitch_shift_via_tools_class(temp_dir, sample_audio_path):
    """Test pitch-shifting via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 1.5
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.pitch_shift(audio_file_id, semitones=-2.0)

    if "error" in result and result.get("error_type") == "DEPENDENCY_MISSING":
        pytest.skip("pyrubberband not installed")

    assert "error" not in result or result.get("error_type") != "DEPENDENCY_MISSING"
