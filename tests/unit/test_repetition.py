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


def _tone_block(freqs, duration, sr):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return sum(np.sin(2 * np.pi * f * t) * 0.3 for f in freqs)


@pytest.mark.asyncio
async def test_detect_repetitions_abab_form(temp_dir, sample_audio_path):
    """An A-B-A-B structure (alternating C major / F# major textures) must
    produce a form whose labels are REUSED for the repeated sections and a
    repetitions list referencing later occurrences."""
    sr = 22050
    a_block = _tone_block([261.63, 329.63, 392.00], 4.0, sr)  # C major
    b_block = _tone_block([369.99, 466.16, 554.37], 4.0, sr)  # F# major
    y = np.concatenate([a_block, b_block, a_block, b_block]).astype(np.float32)

    sf.write(str(sample_audio_path), y, sr)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await detect_repetitions(str(sample_audio_path))

    assert "error" not in result, result
    assert result["form"] != "no_repetition"
    labels = result["form"].split("-")
    # Repeated sections must share labels: fewer distinct labels than segments
    assert len(set(labels)) < len(labels)
    assert len(result["repetitions"]) >= 1
    for rep in result["repetitions"]:
        assert len(rep["repetition_times"]) >= 1
        assert 0.0 <= rep["similarity"] <= 1.0
        # Repetitions must occur after the pattern itself
        assert all(t >= rep["pattern_end"] - 1e-6 for t in rep["repetition_times"])


@pytest.mark.asyncio
async def test_detect_repetitions_completes_quickly_on_long_audio(temp_dir, sample_audio_path):
    """The previous O(n^3+) implementation effectively hung on real-length
    audio. 60 seconds must complete in seconds."""
    import time

    sr = 22050
    rng = np.random.default_rng(42)
    y = (rng.standard_normal(int(sr * 60.0)) * 0.3).astype(np.float32)
    sf.write(str(sample_audio_path), y, sr)

    start = time.monotonic()
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await detect_repetitions(str(sample_audio_path))
    elapsed = time.monotonic() - start

    assert "error" not in result, result
    assert elapsed < 30.0, f"repetition detection took {elapsed:.1f}s"


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
