"""Tests for chord detection with real audio"""

import numpy as np
import pytest
import soundfile as sf

from zikos.mcp.tools.audio.chords import detect_chords


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
            if chord["chord"] != "N.C.":
                assert 0.0 <= chord["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_detect_chords_progression(self, chord_progression_audio):
        """Test chord progression detection"""
        result = await detect_chords(str(chord_progression_audio))

        assert len(result["progression"]) > 0
        assert all(isinstance(chord_name, str) for chord_name in result["progression"])

    @pytest.mark.asyncio
    async def test_detect_chords_segmentation_regression(self, temp_dir):
        """A 4s file (2s C major, 2s A minor) must produce multiple segments with
        at least two different chords. Previously a samples-vs-frames confusion
        made the whole file collapse to a single segment/chord."""
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        c_major = sum(np.sin(2 * np.pi * f * t) * 0.3 for f in [261.63, 329.63, 392.00])
        a_minor = sum(np.sin(2 * np.pi * f * t) * 0.3 for f in [220.00, 261.63, 329.63])

        audio_path = temp_dir / "cmaj_amin.wav"
        sf.write(str(audio_path), np.concatenate([c_major, a_minor]), sr)

        result = await detect_chords(str(audio_path))

        assert not result.get("error"), result
        assert len(result["chords"]) >= 2, "expected multiple chord segments"
        distinct = {c["chord"] for c in result["chords"] if c["chord"] != "N.C."}
        assert len(distinct) >= 2, f"expected >=2 distinct chords, got {distinct}"
        # Standard chord naming: C major is "C", A minor is "Am"
        assert "C" in distinct, distinct
        assert "Am" in distinct, distinct
        # Segment timing should cover the file with sensible durations
        first_half = [c["chord"] for c in result["chords"] if c["time"] < 1.5 and c["chord"] != "N.C."]
        second_half = [c["chord"] for c in result["chords"] if c["time"] > 2.5 and c["chord"] != "N.C."]
        assert "C" in first_half
        assert "Am" in second_half

    @pytest.mark.asyncio
    async def test_detect_chords_silence_labeled_nc(self, temp_dir):
        """Near-silent segments should be labeled N.C. with null confidence."""
        sr = 22050
        t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
        c_major = sum(np.sin(2 * np.pi * f * t) * 0.3 for f in [261.63, 329.63, 392.00])
        silence = np.zeros(int(sr * 2.0))

        audio_path = temp_dir / "chord_then_silence.wav"
        sf.write(str(audio_path), np.concatenate([c_major, silence]), sr)

        result = await detect_chords(str(audio_path))

        assert not result.get("error"), result
        nc_segments = [c for c in result["chords"] if c["chord"] == "N.C."]
        assert len(nc_segments) > 0, "silent half should yield N.C. segments"
        assert all(c["confidence"] is None for c in nc_segments)
        assert "N.C." not in result["progression"]
