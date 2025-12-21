"""Tests for key detection with real audio"""

import numpy as np
import pytest
import soundfile as sf

from zikos.mcp.tools.analysis.audio.key import detect_key


@pytest.fixture
def c_major_scale_audio(temp_dir):
    """Create C major scale audio"""
    sr = 22050
    duration_per_note = 0.5
    notes_hz = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]

    audio_segments = []
    for freq in notes_hz:
        t = np.linspace(0, duration_per_note, int(sr * duration_per_note))
        note = np.sin(2 * np.pi * freq * t) * 0.5
        audio_segments.append(note)

    audio = np.concatenate(audio_segments)
    audio_path = temp_dir / "c_major_scale.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


class TestKeyDetection:
    """Tests for key detection with real audio"""

    @pytest.mark.asyncio
    @pytest.mark.comprehensive
    async def test_detect_key_c_major(self, c_major_scale_audio):
        """Test key detection for C major scale"""
        result = await detect_key(str(c_major_scale_audio))

        assert "key" in result
        assert "confidence" in result
        assert "mode" in result
        assert "tonic" in result

        assert 0.0 <= result["confidence"] <= 1.0
        assert result["mode"] in ["major", "minor"]
        assert isinstance(result["key"], str)

        key_lower = result["key"].lower()
        assert "c" in key_lower

    @pytest.mark.asyncio
    @pytest.mark.comprehensive
    async def test_detect_key_alternative_keys(self, c_major_scale_audio):
        """Test alternative key suggestions"""
        result = await detect_key(str(c_major_scale_audio))

        assert "alternative_keys" in result
        assert isinstance(result["alternative_keys"], list)
