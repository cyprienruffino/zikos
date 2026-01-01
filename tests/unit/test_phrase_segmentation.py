"""Tests for phrase segmentation tool"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.analysis.audio.phrase_segmentation import segment_phrases


@pytest.mark.asyncio
async def test_segment_phrases_success(temp_dir, sample_audio_path):
    """Test successful phrase segmentation"""
    sample_rate = 22050
    duration = 10.0

    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    y[int(0 * sample_rate) : int(4 * sample_rate)] = (
        np.random.randn(int(4 * sample_rate)).astype(np.float32) * 0.5
    )
    y[int(4 * sample_rate) : int(8 * sample_rate)] = (
        np.random.randn(int(4 * sample_rate)).astype(np.float32) * 0.5
    )
    y[int(8 * sample_rate) : int(10 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.5
    )

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert "phrase_count" in result
    assert "average_phrase_length" in result
    assert isinstance(result["phrases"], list)
    assert len(result["phrases"]) > 0

    for phrase in result["phrases"]:
        assert "start" in phrase
        assert "end" in phrase
        assert "type" in phrase
        assert "confidence" in phrase
        assert phrase["start"] < phrase["end"]


@pytest.mark.asyncio
async def test_segment_phrases_too_short(temp_dir, sample_audio_path):
    """Test phrase segmentation with too short audio"""
    sample_rate = 22050
    duration = 0.3
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_segment_phrases_file_not_found(temp_dir):
    """Test phrase segmentation with non-existent file"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases("nonexistent_file.wav")

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_segment_phrases_via_tools_class(temp_dir, sample_audio_path):
    """Test phrase segmentation via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 8.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.segment_phrases(audio_file_id)

    assert "error" not in result
    assert "phrases" in result
    assert len(result["phrases"]) > 0


@pytest.mark.asyncio
async def test_segment_phrases_via_call_tool(temp_dir, sample_audio_path):
    """Test phrase segmentation via call_tool method"""
    sample_rate = 22050
    duration = 6.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.call_tool("segment_phrases", audio_file_id=audio_file_id)

    assert "error" not in result
    assert "phrases" in result


@pytest.mark.asyncio
async def test_segment_phrases_no_phrases_detected(temp_dir, sample_audio_path):
    """Test phrase segmentation when no phrases are detected (returns fallback)"""
    sample_rate = 22050
    duration = 2.0
    # Create very quiet audio that might not trigger phrase detection
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.01

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert "phrase_count" in result
    # Should return at least one phrase (fallback or detected)
    assert len(result["phrases"]) > 0


@pytest.mark.asyncio
async def test_segment_phrases_processing_failure(temp_dir, sample_audio_path):
    """Test phrase segmentation when processing fails"""
    sample_rate = 22050
    duration = 2.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with patch("librosa.load", side_effect=Exception("Processing error")):
            result = await segment_phrases(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "PROCESSING_FAILED"
    assert "message" in result


@pytest.mark.asyncio
async def test_segment_phrases_energy_levels(temp_dir, sample_audio_path):
    """Test phrase segmentation with different energy levels"""
    sample_rate = 22050
    duration = 6.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    # Create quiet phrase
    y[int(0 * sample_rate) : int(2 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.1
    )
    # Create energetic phrase
    y[int(2 * sample_rate) : int(4 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.9
    )
    # Create melodic phrase
    y[int(4 * sample_rate) : int(6 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.5
    )

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert len(result["phrases"]) > 0

    # Check that different phrase types are detected
    phrase_types = [p.get("type") for p in result["phrases"]]
    assert any(t in phrase_types for t in ["quiet", "energetic", "melodic"])


@pytest.mark.asyncio
async def test_segment_phrases_no_boundaries_detected(temp_dir, sample_audio_path):
    """Test phrase segmentation when no boundaries are detected (fallback case)"""
    sample_rate = 22050
    duration = 2.0
    y = np.ones(int(sample_rate * duration), dtype=np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert len(result["phrases"]) > 0


@pytest.mark.asyncio
async def test_segment_phrases_empty_segments(temp_dir, sample_audio_path):
    """Test phrase segmentation with edge case of empty segments"""
    sample_rate = 22050
    duration = 3.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    y[int(0.5 * sample_rate) : int(1.5 * sample_rate)] = (
        np.random.randn(int(1.0 * sample_rate)).astype(np.float32) * 0.5
    )

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result


@pytest.mark.asyncio
async def test_segment_phrases_with_path_string(temp_dir, sample_audio_path):
    """Test phrase segmentation with path string instead of file ID"""
    sample_rate = 22050
    duration = 5.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result


@pytest.mark.asyncio
async def test_segment_phrases_with_silence_boundaries(temp_dir, sample_audio_path):
    """Test phrase segmentation with silence boundaries (lines 52-59)"""
    sample_rate = 22050
    duration = 6.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    y[int(0 * sample_rate) : int(2 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.5
    )
    y[int(2.5 * sample_rate) : int(4.5 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.5
    )

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert len(result["phrases"]) > 0


@pytest.mark.asyncio
async def test_segment_phrases_phrase_continues_to_end(temp_dir, sample_audio_path):
    """Test phrase segmentation when phrase continues to end (line 61-65)"""
    sample_rate = 22050
    duration = 4.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert len(result["phrases"]) > 0


@pytest.mark.asyncio
async def test_segment_phrases_quiet_phrase_type(temp_dir, sample_audio_path):
    """Test phrase segmentation with quiet phrase (energy_level < 0.3, line 90)"""
    sample_rate = 22050
    duration = 4.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    y[int(0.5 * sample_rate) : int(2.5 * sample_rate)] = (
        np.random.randn(int(2 * sample_rate)).astype(np.float32) * 0.1
    )

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    if len(result["phrases"]) > 0:
        phrase_types = [p.get("type") for p in result["phrases"]]
        assert any(t in phrase_types for t in ["quiet", "melodic", "energetic"])


@pytest.mark.asyncio
async def test_segment_phrases_empty_phrases_after_processing(temp_dir, sample_audio_path):
    """Test phrase segmentation when phrases list is empty after processing (line 106)"""
    sample_rate = 22050
    duration = 3.0
    y = np.zeros(int(sample_rate * duration), dtype=np.float32)

    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with patch("librosa.feature.rms", return_value=np.array([[0.0] * 100])):
            result = await segment_phrases(str(sample_audio_path))

    assert "error" not in result
    assert "phrases" in result
    assert len(result["phrases"]) > 0
