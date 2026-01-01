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


@pytest.mark.asyncio
async def test_comprehensive_analysis_processing_error(temp_dir, sample_audio_path):
    """Test comprehensive analysis with processing error"""
    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with patch(
            "zikos.mcp.tools.analysis.audio.tempo.analyze_tempo",
            side_effect=Exception("Processing failed"),
        ):
            result = await comprehensive_analysis(str(sample_audio_path))

    assert result["error"] is True
    assert result["error_type"] == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_comprehensive_analysis_too_short_audio(temp_dir, sample_audio_path):
    """Test comprehensive analysis with too short audio"""
    sample_rate = 22050
    duration = 0.3
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await comprehensive_analysis(audio_file_id)

    assert "error" in result
    assert result["error_type"] == "TOO_SHORT"


@pytest.mark.asyncio
async def test_comprehensive_analysis_with_high_scores(temp_dir, sample_audio_path):
    """Test comprehensive analysis with high scores (>= 0.85)"""
    sample_rate = 22050
    duration = 5.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with (
            patch("zikos.mcp.tools.analysis.audio.tempo.analyze_tempo") as mock_tempo,
            patch("zikos.mcp.tools.analysis.audio.pitch.detect_pitch") as mock_pitch,
            patch("zikos.mcp.tools.analysis.audio.rhythm.analyze_rhythm") as mock_rhythm,
            patch("zikos.mcp.tools.analysis.audio.dynamics.analyze_dynamics") as mock_dynamics,
            patch(
                "zikos.mcp.tools.analysis.audio.articulation.analyze_articulation"
            ) as mock_articulation,
            patch("zikos.mcp.tools.analysis.audio.timbre.analyze_timbre") as mock_timbre,
            patch("zikos.mcp.tools.analysis.audio.key.detect_key") as mock_key,
            patch("zikos.mcp.tools.analysis.audio.chords.detect_chords") as mock_chords,
            patch(
                "zikos.mcp.tools.analysis.audio.phrase_segmentation.segment_phrases"
            ) as mock_phrases,
        ):
            mock_tempo.return_value = {"tempo_stability_score": 0.90, "bpm": 120}
            mock_pitch.return_value = {"intonation_accuracy": 0.90, "pitch_stability": 0.88}
            mock_rhythm.return_value = {"timing_accuracy": 0.92}
            mock_dynamics.return_value = {"dynamic_consistency": 0.85}
            mock_articulation.return_value = {"articulation_consistency": 0.82}
            mock_timbre.return_value = {"timbre_consistency": 0.83}
            mock_key.return_value = {"detected_key": "C major"}
            mock_chords.return_value = {"chords": []}
            mock_phrases.return_value = {"phrases": []}

            result = await comprehensive_analysis(audio_file_id)

    assert "error" not in result
    assert "strengths" in result
    assert len(result["strengths"]) > 0


@pytest.mark.asyncio
async def test_comprehensive_analysis_with_low_scores(temp_dir, sample_audio_path):
    """Test comprehensive analysis with low scores (< 0.70)"""
    sample_rate = 22050
    duration = 5.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with (
            patch("zikos.mcp.tools.analysis.audio.tempo.analyze_tempo") as mock_tempo,
            patch("zikos.mcp.tools.analysis.audio.pitch.detect_pitch") as mock_pitch,
            patch("zikos.mcp.tools.analysis.audio.rhythm.analyze_rhythm") as mock_rhythm,
            patch("zikos.mcp.tools.analysis.audio.dynamics.analyze_dynamics") as mock_dynamics,
            patch(
                "zikos.mcp.tools.analysis.audio.articulation.analyze_articulation"
            ) as mock_articulation,
            patch("zikos.mcp.tools.analysis.audio.timbre.analyze_timbre") as mock_timbre,
            patch("zikos.mcp.tools.analysis.audio.key.detect_key") as mock_key,
            patch("zikos.mcp.tools.analysis.audio.chords.detect_chords") as mock_chords,
            patch(
                "zikos.mcp.tools.analysis.audio.phrase_segmentation.segment_phrases"
            ) as mock_phrases,
        ):
            mock_tempo.return_value = {
                "tempo_stability_score": 0.65,
                "bpm": 120,
                "rushing_detected": True,
            }
            mock_pitch.return_value = {"intonation_accuracy": 0.65, "pitch_stability": 0.68}
            mock_rhythm.return_value = {"timing_accuracy": 0.60}
            mock_dynamics.return_value = {"dynamic_consistency": 0.60}
            mock_articulation.return_value = {"articulation_consistency": 0.62}
            mock_timbre.return_value = {"timbre_consistency": 0.64}
            mock_key.return_value = {"detected_key": "C major"}
            mock_chords.return_value = {"chords": []}
            mock_phrases.return_value = {"phrases": []}

            result = await comprehensive_analysis(audio_file_id)

    assert "error" not in result
    assert "weaknesses" in result
    assert len(result["weaknesses"]) > 0
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_comprehensive_analysis_with_errors_in_sub_analyses(temp_dir, sample_audio_path):
    """Test comprehensive analysis when sub-analyses return errors"""
    sample_rate = 22050
    duration = 5.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    audio_file_id = sample_audio_path.stem

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        with (
            patch("zikos.mcp.tools.analysis.audio.tempo.analyze_tempo") as mock_tempo,
            patch("zikos.mcp.tools.analysis.audio.pitch.detect_pitch") as mock_pitch,
            patch("zikos.mcp.tools.analysis.audio.rhythm.analyze_rhythm") as mock_rhythm,
            patch("zikos.mcp.tools.analysis.audio.dynamics.analyze_dynamics") as mock_dynamics,
            patch(
                "zikos.mcp.tools.analysis.audio.articulation.analyze_articulation"
            ) as mock_articulation,
            patch("zikos.mcp.tools.analysis.audio.timbre.analyze_timbre") as mock_timbre,
            patch("zikos.mcp.tools.analysis.audio.key.detect_key") as mock_key,
            patch("zikos.mcp.tools.analysis.audio.chords.detect_chords") as mock_chords,
            patch(
                "zikos.mcp.tools.analysis.audio.phrase_segmentation.segment_phrases"
            ) as mock_phrases,
        ):
            mock_tempo.return_value = {"tempo_stability_score": 0.80, "bpm": 120}
            mock_pitch.return_value = {"intonation_accuracy": 0.75, "pitch_stability": 0.78}
            mock_rhythm.return_value = {"timing_accuracy": 0.82}
            mock_dynamics.return_value = {"error": True, "error_type": "PROCESSING_FAILED"}
            mock_articulation.return_value = {"error": True, "error_type": "PROCESSING_FAILED"}
            mock_timbre.return_value = {"error": True, "error_type": "PROCESSING_FAILED"}
            mock_key.return_value = {"error": True, "error_type": "PROCESSING_FAILED"}
            mock_chords.return_value = {"error": True, "error_type": "PROCESSING_FAILED"}
            mock_phrases.return_value = {"error": True, "error_type": "PROCESSING_FAILED"}

            result = await comprehensive_analysis(audio_file_id)

    assert "error" not in result
    assert "dynamics" in result
    assert result["dynamics"] == {}
    assert "frequency" in result
    assert result["frequency"]["timbre"] == {}


@pytest.mark.asyncio
async def test_comprehensive_analysis_with_path_string(temp_dir, sample_audio_path):
    """Test comprehensive analysis with path string instead of file ID"""
    sample_rate = 22050
    duration = 5.0
    y = np.random.randn(int(sample_rate * duration)).astype(np.float32) * 0.5
    sf.write(str(sample_audio_path), y, sample_rate)

    with patch.object(settings, "audio_storage_path", str(temp_dir)):
        result = await comprehensive_analysis(str(sample_audio_path))

    assert "error" not in result
    assert "overall_score" in result
