"""Tests for instrument metrics tool"""

import numpy as np
import pytest
import soundfile as sf

from zikos.mcp.tools.audio.instrument_detector import detect_instrument


class TestDetectInstrument:
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self, tmp_path):
        audio = np.sin(2 * np.pi * 100 * np.linspace(0, 2, 44100 * 2)).astype(np.float32)
        path = tmp_path / "tone.wav"
        sf.write(str(path), audio, 44100)

        result = await detect_instrument(str(path))

        for key in (
            "spectral_centroid_hz",
            "f0_median_hz",
            "f0_min_hz",
            "f0_max_hz",
            "pitch_confidence",
            "harmonic_ratio",
        ):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_low_frequency_sine_has_low_centroid(self, tmp_path):
        # 100 Hz pure sine — matches bass-like spectral profile
        t = np.linspace(0, 2, 44100 * 2)
        audio = np.sin(2 * np.pi * 100 * t).astype(np.float32)
        path = tmp_path / "bass_tone.wav"
        sf.write(str(path), audio, 44100)

        result = await detect_instrument(str(path))

        assert result["spectral_centroid_hz"] < 900
        assert result["f0_median_hz"] is not None
        assert result["f0_median_hz"] < 350

    @pytest.mark.asyncio
    async def test_high_frequency_signal_has_high_centroid(self, tmp_path):
        # Mix of high harmonics — piano-like bright spectrum
        t = np.linspace(0, 2, 44100 * 2)
        audio = sum(np.sin(2 * np.pi * f * t) for f in [440, 880, 1320, 1760, 2200]).astype(
            np.float32
        )
        audio /= np.max(np.abs(audio))
        path = tmp_path / "bright_tone.wav"
        sf.write(str(path), audio, 44100)

        result = await detect_instrument(str(path))

        assert result["spectral_centroid_hz"] > 900

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self):
        result = await detect_instrument("/nonexistent/file.wav")
        assert result.get("error") is True
        assert result.get("error_type") == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_pitch_confidence_between_0_and_1(self, tmp_path):
        audio = np.sin(2 * np.pi * 200 * np.linspace(0, 2, 44100 * 2)).astype(np.float32)
        path = tmp_path / "tone.wav"
        sf.write(str(path), audio, 44100)

        result = await detect_instrument(str(path))

        assert 0.0 <= result["pitch_confidence"] <= 1.0
