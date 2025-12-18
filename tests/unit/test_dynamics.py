"""Tests for dynamics analysis with real audio"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.zikos.mcp.tools.audio.dynamics import analyze_dynamics


@pytest.fixture
def real_audio_file(temp_dir):
    """Create a real audio file with varying dynamics"""
    sr = 22050
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))

    # Create audio with varying dynamics: quiet -> loud -> quiet
    audio = np.sin(2 * np.pi * 440 * t) * np.concatenate(
        [
            np.linspace(0.1, 0.1, len(t) // 3),  # Quiet start
            np.linspace(0.1, 0.9, len(t) // 3),  # Crescendo
            np.linspace(0.9, 0.2, len(t) // 3),  # Diminuendo
        ]
    )

    audio_path = temp_dir / "dynamics_test.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


class TestDynamicsAnalysis:
    """Tests for dynamics analysis with real audio"""

    @pytest.mark.asyncio
    async def test_analyze_dynamics_basic(self, real_audio_file):
        """Test basic dynamics analysis with real audio"""
        result = await analyze_dynamics(str(real_audio_file))

        assert "average_rms" in result
        assert "peak_amplitude" in result
        assert "dynamic_range_db" in result
        assert "dynamic_consistency" in result

        assert isinstance(result["average_rms"], int | float)
        assert isinstance(result["peak_amplitude"], int | float)
        assert isinstance(result["dynamic_range_db"], int | float)
        assert 0.0 <= result["dynamic_consistency"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_dynamics_amplitude_envelope(self, real_audio_file):
        """Test amplitude envelope extraction"""
        result = await analyze_dynamics(str(real_audio_file))

        assert "amplitude_envelope" in result
        assert isinstance(result["amplitude_envelope"], list)
        if len(result["amplitude_envelope"]) > 0:
            envelope_point = result["amplitude_envelope"][0]
            assert "time" in envelope_point
            assert "rms" in envelope_point

    @pytest.mark.asyncio
    async def test_analyze_dynamics_consistent_volume(self, temp_dir):
        """Test dynamics analysis with consistent volume"""
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        audio = np.sin(2 * np.pi * 440 * t) * 0.5  # Constant amplitude

        audio_path = temp_dir / "consistent.wav"
        sf.write(str(audio_path), audio, sr)

        result = await analyze_dynamics(str(audio_path))

        assert result["dynamic_consistency"] > 0.8

    @pytest.mark.asyncio
    async def test_analyze_dynamics_varying_volume(self, temp_dir):
        """Test dynamics analysis with varying volume"""
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration))
        # Large dynamic variation
        envelope = np.linspace(0.1, 0.9, len(t))
        audio = np.sin(2 * np.pi * 440 * t) * envelope

        audio_path = temp_dir / "varying.wav"
        sf.write(str(audio_path), audio, sr)

        result = await analyze_dynamics(str(audio_path))

        assert result["dynamic_range_db"] > 10.0
        assert result["dynamic_consistency"] < 0.7
