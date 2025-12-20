"""Tests for chord detection with real audio"""

import numpy as np
import pytest
import soundfile as sf

from zikos.mcp.tools.analysis.audio.chords import detect_chords


@pytest.fixture
def chord_progression_audio(temp_dir):
    """Create audio with chord progression"""
    sr = 22050
    duration_per_chord = 1.0

    # C major chord (C, E, G)
    c_maj = np.array([261.63, 329.63, 392.00])
    # A minor chord (A, C, E)
    a_min = np.array([440.00, 523.25, 659.25])

    audio_segments = []
    for chord_freqs in [c_maj, a_min, c_maj, a_min]:
        t = np.linspace(0, duration_per_chord, int(sr * duration_per_chord))
        chord_audio = sum(np.sin(2 * np.pi * freq * t) * 0.3 for freq in chord_freqs)
        audio_segments.append(chord_audio)

    audio = np.concatenate(audio_segments)
    audio_path = temp_dir / "chords.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


class TestChordDetection:
    """Tests for chord detection with real audio"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_detect_chords_basic(self, chord_progression_audio):
        """Test basic chord detection"""
        result = await detect_chords(str(chord_progression_audio))

        assert "chords" in result
        assert "progression" in result
        assert isinstance(result["chords"], list)
        assert isinstance(result["progression"], list)

        if len(result["chords"]) > 0:
            chord = result["chords"][0]
            assert "time" in chord
            assert "duration" in chord
            assert "chord" in chord
            assert "confidence" in chord
            assert 0.0 <= chord["confidence"] <= 1.0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_detect_chords_progression(self, chord_progression_audio):
        """Test chord progression detection"""
        result = await detect_chords(str(chord_progression_audio))

        assert len(result["progression"]) > 0
        assert all(isinstance(chord_name, str) for chord_name in result["progression"])
