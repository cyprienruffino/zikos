"""Tests for instrument detection"""

from unittest.mock import patch

import numpy as np
import pytest

from zikos.mcp.tools.audio.instrument_detector import (
    _classify,
    check_instrument_mismatch,
    detect_instrument,
)


class TestClassify:
    def test_low_centroid_low_f0_is_bass(self):
        cls, conf = _classify(centroid_hz=600.0, median_f0=100.0)
        assert cls == "bass"
        assert conf >= 0.65

    def test_very_low_centroid_is_bass_high_confidence(self):
        cls, conf = _classify(centroid_hz=400.0, median_f0=80.0)
        assert cls == "bass"
        assert conf >= 0.8

    def test_high_centroid_is_piano(self):
        cls, conf = _classify(centroid_hz=1500.0, median_f0=440.0)
        assert cls == "piano"
        assert conf >= 0.6

    def test_very_high_centroid_is_piano_high_confidence(self):
        cls, conf = _classify(centroid_hz=2000.0, median_f0=300.0)
        assert cls == "piano"
        assert conf >= 0.75

    def test_mid_centroid_is_guitar(self):
        cls, conf = _classify(centroid_hz=1000.0, median_f0=200.0)
        assert cls == "guitar"

    def test_unknown_when_very_low_centroid_no_f0(self):
        # No F0 should still classify as bass if centroid is low
        cls, conf = _classify(centroid_hz=500.0, median_f0=None)
        assert cls == "bass"

    def test_piano_vs_bass_boundary(self):
        # centroid=1270 Hz (piano from session log) should be piano
        cls, _ = _classify(centroid_hz=1270.0, median_f0=300.0)
        assert cls == "piano"

        # centroid=650 Hz (bass from session log) should be bass
        cls, _ = _classify(centroid_hz=650.0, median_f0=100.0)
        assert cls == "bass"


class TestCheckInstrumentMismatch:
    def test_no_warning_when_instruments_match(self):
        assert check_instrument_mismatch("bass", ["guitar", "basse"]) is None

    def test_no_warning_when_instruments_match_english(self):
        assert check_instrument_mismatch("bass", ["bass", "guitar"]) is None

    def test_warning_when_mismatch(self):
        result = check_instrument_mismatch("piano", ["guitar", "basse"])
        assert result is not None
        assert "piano" in result
        assert "guitar" in result or "basse" in result

    def test_no_warning_for_unknown_class(self):
        assert check_instrument_mismatch("unknown", ["guitar"]) is None

    def test_no_warning_when_no_user_instruments(self):
        assert check_instrument_mismatch("piano", []) is None

    def test_contrebasse_matches_bass(self):
        assert check_instrument_mismatch("bass", ["contrebasse"]) is None

    def test_piano_keywords(self):
        assert check_instrument_mismatch("piano", ["clavier"]) is None
        assert check_instrument_mismatch("piano", ["keyboard"]) is None


class TestDetectInstrument:
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self, tmp_path):
        import soundfile as sf

        audio = np.sin(2 * np.pi * 100 * np.linspace(0, 2, 44100 * 2)).astype(np.float32)
        path = tmp_path / "bass.wav"
        sf.write(str(path), audio, 44100)

        result = await detect_instrument(str(path))

        assert "detected_class" in result
        assert "confidence" in result
        assert "spectral_centroid_hz" in result
        assert "median_f0_hz" in result

    @pytest.mark.asyncio
    async def test_low_frequency_sine_classified_as_bass(self, tmp_path):
        import soundfile as sf

        # 100 Hz sine — bass-like fundamental, low spectral centroid
        t = np.linspace(0, 2, 44100 * 2)
        audio = np.sin(2 * np.pi * 100 * t).astype(np.float32)
        path = tmp_path / "bass_tone.wav"
        sf.write(str(path), audio, 44100)

        result = await detect_instrument(str(path))

        assert result.get("detected_class") == "bass"

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error(self):
        result = await detect_instrument("/nonexistent/file.wav")
        assert result.get("error") is True
        assert result.get("error_type") == "FILE_NOT_FOUND"
