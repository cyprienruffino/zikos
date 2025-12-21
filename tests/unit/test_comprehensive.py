"""Tests for comprehensive analysis tool"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.analysis.audio.comprehensive import comprehensive_analysis


@pytest.mark.asyncio
@pytest.mark.comprehensive
async def test_comprehensive_analysis_success(temp_dir, sample_audio_path):
    """Test successful comprehensive analysis"""
    sample_rate = 22050
    duration = 5.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await comprehensive_analysis(audio_file_id)

    assert "error" not in result
    assert "timing" in result
    assert "pitch" in result
    assert "dynamics" in result
    assert "frequency" in result
    assert "musical_structure" in result
    assert "overall_score" in result
    assert "strengths" in result
    assert "weaknesses" in result
    assert "recommendations" in result
    assert isinstance(result["overall_score"], float)
    assert 0.0 <= result["overall_score"] <= 1.0


@pytest.mark.asyncio
async def test_comprehensive_analysis_file_not_found(temp_dir):
    """Test comprehensive analysis with non-existent file"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await comprehensive_analysis("nonexistent_file")

    assert result["error"] is True
    assert result["error_type"] == "FILE_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.comprehensive
async def test_comprehensive_analysis_via_tools_class(temp_dir, sample_audio_path):
    """Test comprehensive analysis via AudioAnalysisTools class"""
    sample_rate = 22050
    duration = 4.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.comprehensive_analysis(audio_file_id)

    assert "error" not in result
    assert "overall_score" in result


@pytest.mark.asyncio
@pytest.mark.comprehensive
async def test_comprehensive_analysis_via_call_tool(temp_dir, sample_audio_path):
    """Test comprehensive analysis via call_tool method"""
    sample_rate = 22050
    duration = 3.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5

    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem
    tools = AudioAnalysisTools()

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await tools.call_tool("comprehensive_analysis", audio_file_id=audio_file_id)

    assert "error" not in result
    assert "overall_score" in result
