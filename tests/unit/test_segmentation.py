"""Tests for audio segmentation tool"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.audio import AudioAnalysisTools
from zikos.mcp.tools.audio.segmentation import segment_audio


@pytest.mark.asyncio
async def test_segment_audio_success(temp_dir, sample_audio_path):
    """Test successful audio segmentation"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_audio(audio_file_id, start_time=2.0, end_time=5.0)

    assert "error" not in result
    assert "new_audio_file_id" in result
    assert result["original_audio_file_id"] == audio_file_id
    assert result["start_time"] == 2.0
    assert result["end_time"] == 5.0
    assert result["duration"] == pytest.approx(3.0, abs=0.1)

    new_audio_path = Path(temp_dir) / f"{result['new_audio_file_id']}.wav"
    assert new_audio_path.exists()

    y_seg, sr_seg = sf.read(str(new_audio_path))
    assert sr_seg == sample_rate
    assert len(y_seg) / sr_seg == pytest.approx(3.0, abs=0.1)


@pytest.mark.asyncio
async def test_segment_audio_invalid_start_time(temp_dir, sample_audio_path):
    """Test segmentation with invalid start_time"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_audio(audio_file_id, start_time=-1.0, end_time=5.0)

    assert result["error"] is True
    assert result["error_type"] == "INVALID_PARAMETER"
    assert "start_time must be non-negative" in result["message"]


@pytest.mark.asyncio
async def test_segment_audio_end_before_start(temp_dir, sample_audio_path):
    """Test segmentation with end_time before start_time"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_audio(audio_file_id, start_time=5.0, end_time=2.0)

    assert result["error"] is True
    assert result["error_type"] == "INVALID_PARAMETER"
    assert "end_time must be greater than start_time" in result["message"]


@pytest.mark.asyncio
async def test_segment_audio_start_exceeds_duration(temp_dir, sample_audio_path):
    """Test segmentation with start_time exceeding audio duration"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_audio(audio_file_id, start_time=15.0, end_time=20.0)

    assert result["error"] is True
    assert result["error_type"] == "INVALID_PARAMETER"
    assert "exceeds audio duration" in result["message"]


@pytest.mark.asyncio
async def test_segment_audio_end_exceeds_duration(temp_dir, sample_audio_path):
    """Test segmentation with end_time exceeding audio duration (should clamp)"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_audio(audio_file_id, start_time=8.0, end_time=15.0)

    assert "error" not in result
    assert result["end_time"] == pytest.approx(10.0, abs=0.1)
    assert result["duration"] == pytest.approx(2.0, abs=0.1)


@pytest.mark.asyncio
async def test_segment_audio_file_not_found(temp_dir):
    """Test segmentation with non-existent audio file"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_audio("nonexistent_file", start_time=0.0, end_time=1.0)

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_segment_audio_via_tools_class(temp_dir, sample_audio_path):
    """Test segmentation via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.segment_audio(audio_file_id, start_time=1.0, end_time=3.0)

    assert "error" not in result
    assert "new_audio_file_id" in result
    assert result["duration"] == pytest.approx(2.0, abs=0.1)


@pytest.mark.asyncio
async def test_segment_audio_via_call_tool(temp_dir, sample_audio_path):
    """Test segmentation via call_tool method"""
    sample_rate = 22050
    duration = 10.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.call_tool(
            "segment_audio",
            audio_file_id=audio_file_id,
            start_time=0.5,
            end_time=2.5,
        )

    assert "error" not in result
    assert "new_audio_file_id" in result
    assert result["duration"] == pytest.approx(2.0, abs=0.1)
