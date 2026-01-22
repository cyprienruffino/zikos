"""Tests for repetition detection tool"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.audio.repetition import detect_repetitions


@pytest.mark.asyncio
async def test_detect_repetitions_success(temp_dir, sample_audio_path):
    """Test successful repetition detection"""
    sample_rate = 22050

    pattern = np.random.randn(int(sample_rate * 2.0)).astype(np.float32) * 0.5
    y = np.concatenate([pattern, pattern, pattern, pattern])

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await detect_repetitions(str(sample_audio_path))

    assert "error" not in result
    assert "repetitions" in result
    assert "form" in result
    assert isinstance(result["repetitions"], list)


@pytest.mark.asyncio
async def test_detect_repetitions_too_short(temp_dir, sample_audio_path):
    """Test repetition detection with too short audio"""
    sample_rate = 22050
    duration = 1.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await detect_repetitions(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_detect_repetitions_file_not_found(temp_dir):
    """Test repetition detection with non-existent file"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await detect_repetitions("nonexistent_file.wav")

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_detect_repetitions_via_tools_class(temp_dir, sample_audio_path):
    """Test repetition detection via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 6.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.detect_repetitions(audio_file_id)

    assert "error" not in result
    assert "repetitions" in result
    assert "form" in result
