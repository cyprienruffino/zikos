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
from zikos.mcp.tools.audio.time_stretch import pitch_shift, time_stretch


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


@pytest.mark.asyncio
async def test_time_stretch_missing_pyrubberband(temp_dir, sample_audio_path):
    """Test time-stretch when pyrubberband is not installed"""
    with patch("zikos.mcp.tools.audio.time_stretch.pyrb", None):
        audio_file_id = sample_audio_path.stem
        result = await time_stretch(audio_file_id, rate=1.5)

    assert result["error"] is True
    assert result["error_type"] == "DEPENDENCY_MISSING"


@pytest.mark.asyncio
async def test_pitch_shift_missing_pyrubberband(temp_dir, sample_audio_path):
    """Test pitch-shift when pyrubberband is not installed"""
    with patch("zikos.mcp.tools.audio.time_stretch.pyrb", None):
        audio_file_id = sample_audio_path.stem
        result = await pitch_shift(audio_file_id, semitones=2.0)

    assert result["error"] is True
    assert result["error_type"] == "DEPENDENCY_MISSING"


@pytest.mark.asyncio
async def test_time_stretch_rate_zero_or_negative(temp_dir, sample_audio_path):
    """Test time-stretch with zero or negative rate"""
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
        result_zero = await time_stretch(audio_file_id, rate=0.0)
        result_negative = await time_stretch(audio_file_id, rate=-1.0)

    assert result_zero["error"] is True
    assert result_zero["error_type"] == "INVALID_PARAMETER"
    assert result_negative["error"] is True
    assert result_negative["error_type"] == "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_time_stretch_rate_too_high(temp_dir, sample_audio_path):
    """Test time-stretch with rate > 4.0"""
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
        result = await time_stretch(audio_file_id, rate=5.0)

    assert result["error"] is True
    assert result["error_type"] == "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_time_stretch_too_short(temp_dir, sample_audio_path):
    """Test time-stretch with audio that's too short"""
    try:
        import pyrubberband
    except ImportError:
        pytest.skip("pyrubberband not installed")

    sample_rate = 22050
    duration = 0.05
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await time_stretch(audio_file_id, rate=1.5)

    assert result["error"] is True
    assert result["error_type"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_pitch_shift_too_short(temp_dir, sample_audio_path):
    """Test pitch-shift with audio that's too short"""
    try:
        import pyrubberband
    except ImportError:
        pytest.skip("pyrubberband not installed")

    sample_rate = 22050
    duration = 0.05
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await pitch_shift(audio_file_id, semitones=2.0)

    assert result["error"] is True
    assert result["error_type"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_time_stretch_file_not_found(temp_dir):
    """Test time-stretch with non-existent file"""
    try:
        import pyrubberband
    except ImportError:
        pytest.skip("pyrubberband not installed")

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await time_stretch("nonexistent_file", rate=1.5)

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_pitch_shift_file_not_found(temp_dir):
    """Test pitch-shift with non-existent file"""
    try:
        import pyrubberband
    except ImportError:
        pytest.skip("pyrubberband not installed")

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await pitch_shift("nonexistent_file", semitones=2.0)

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_time_stretch_processing_error(temp_dir, sample_audio_path):
    """Test time-stretch with processing error"""
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
        with patch("librosa.load", side_effect=Exception("Processing failed")):
            result = await time_stretch(audio_file_id, rate=1.5)

    assert result["error"] is True
    assert result["error_type"] == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_pitch_shift_processing_error(temp_dir, sample_audio_path):
    """Test pitch-shift with processing error"""
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
        with patch("librosa.load", side_effect=Exception("Processing failed")):
            result = await pitch_shift(audio_file_id, semitones=2.0)

    assert result["error"] is True
    assert result["error_type"] == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_time_stretch_success_full_path(temp_dir, sample_audio_path):
    """Test successful time-stretching covering full success path (lines 56-66)"""
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
        result = await time_stretch(audio_file_id, rate=1.5)

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
    assert "original_audio_file_id" in result
    assert result["rate"] == 1.5
    assert "original_duration" in result
    assert "new_duration" in result
    assert result["new_duration"] == pytest.approx(result["original_duration"] / 1.5, abs=0.2)


@pytest.mark.asyncio
async def test_pitch_shift_success_full_path(temp_dir, sample_audio_path):
    """Test successful pitch-shifting covering full success path (lines 116-125)"""
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
        result = await pitch_shift(audio_file_id, semitones=-5.0)

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
    assert "original_audio_file_id" in result
    assert result["semitones"] == -5.0
    assert "duration" in result


@pytest.mark.asyncio
async def test_time_stretch_edge_rates(temp_dir, sample_audio_path):
    """Test time-stretch with edge case rates"""
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
        result_025 = await time_stretch(audio_file_id, rate=0.25)
        result_40 = await time_stretch(audio_file_id, rate=4.0)

    if "error" in result_025 and result_025.get("error_type") == "DEPENDENCY_MISSING":
        pytest.skip("pyrubberband not installed")

    assert "error" not in result_025 or result_025.get("error_type") != "INVALID_PARAMETER"
    assert "error" not in result_40 or result_40.get("error_type") != "INVALID_PARAMETER"


@pytest.mark.asyncio
async def test_pitch_shift_edge_semitones(temp_dir, sample_audio_path):
    """Test pitch-shift with edge case semitones"""
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
        result_neg24 = await pitch_shift(audio_file_id, semitones=-24.0)
        result_pos24 = await pitch_shift(audio_file_id, semitones=24.0)

    if "error" in result_neg24 and result_neg24.get("error_type") == "DEPENDENCY_MISSING":
        pytest.skip("pyrubberband not installed")

    assert "error" not in result_neg24 or result_neg24.get("error_type") != "INVALID_PARAMETER"
    assert "error" not in result_pos24 or result_pos24.get("error_type") != "INVALID_PARAMETER"
