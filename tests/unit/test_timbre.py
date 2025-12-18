"""Tests for timbre analysis with real audio"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.zikos.mcp.tools.audio.timbre import analyze_timbre


@pytest.fixture
def bright_audio_file(temp_dir):
    """Create audio with bright timbre (high frequencies)"""
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))

    # Bright sound: fundamental + many high harmonics
    audio = (
        np.sin(2 * np.pi * 440 * t) * 0.5
        + np.sin(2 * np.pi * 880 * t) * 0.3
        + np.sin(2 * np.pi * 1320 * t) * 0.2
        + np.sin(2 * np.pi * 1760 * t) * 0.1
    )

    audio_path = temp_dir / "bright.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


@pytest.fixture
def warm_audio_file(temp_dir):
    """Create audio with warm timbre (low frequencies)"""
    sr = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))

    # Warm sound: fundamental + low harmonics
    audio = (
        np.sin(2 * np.pi * 220 * t) * 0.6
        + np.sin(2 * np.pi * 440 * t) * 0.3
        + np.sin(2 * np.pi * 660 * t) * 0.1
    )

    audio_path = temp_dir / "warm.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


class TestTimbreAnalysis:
    """Tests for timbre analysis with real audio"""

    @pytest.mark.asyncio
    async def test_analyze_timbre_basic(self, bright_audio_file):
        """Test basic timbre analysis"""
        result = await analyze_timbre(str(bright_audio_file))

        assert "brightness" in result
        assert "warmth" in result
        assert "spectral_centroid" in result
        assert "timbre_consistency" in result

        assert 0.0 <= result["brightness"] <= 1.0
        assert 0.0 <= result["warmth"] <= 1.0
        assert isinstance(result["spectral_centroid"], int | float)
        assert result["spectral_centroid"] > 0

    @pytest.mark.asyncio
    async def test_analyze_timbre_bright_vs_warm(self, bright_audio_file, warm_audio_file):
        """Test that bright audio has higher brightness than warm"""
        bright_result = await analyze_timbre(str(bright_audio_file))
        warm_result = await analyze_timbre(str(warm_audio_file))

        assert bright_result["brightness"] > warm_result["brightness"]
        assert bright_result["spectral_centroid"] > warm_result["spectral_centroid"]
        assert warm_result["warmth"] > bright_result["warmth"]

    @pytest.mark.asyncio
    async def test_analyze_timbre_spectral_features(self, bright_audio_file):
        """Test spectral feature extraction"""
        result = await analyze_timbre(str(bright_audio_file))

        assert "spectral_rolloff" in result
        assert "spectral_bandwidth" in result
        assert isinstance(result["spectral_rolloff"], int | float)
        assert isinstance(result["spectral_bandwidth"], int | float)
