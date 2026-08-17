"""Tests for articulation analysis with real audio"""

import numpy as np
import pytest
import soundfile as sf

from zikos.mcp.tools.audio.articulation import analyze_articulation


@pytest.fixture
def staccato_audio(temp_dir):
    """Create staccato audio (short notes with gaps)"""
    sr = 22050
    note_duration = 0.05
    gap_duration = 0.25

    notes_hz = [440.0, 493.88, 523.25, 587.33]
    audio_segments = []

    for freq in notes_hz:
        t_note = np.linspace(0, note_duration, int(sr * note_duration))
        note = np.sin(2 * np.pi * freq * t_note) * 0.5
        audio_segments.append(note)

        t_gap = np.linspace(0, gap_duration, int(sr * gap_duration))
        gap = np.zeros_like(t_gap)
        audio_segments.append(gap)

    audio = np.concatenate(audio_segments)
    audio_path = temp_dir / "staccato.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


@pytest.fixture
def legato_audio(temp_dir):
    """Create legato audio (smooth, connected notes)"""
    sr = 22050
    duration_per_note = 0.5

    notes_hz = [440.0, 493.88, 523.25, 587.33]
    audio_segments = []

    for freq in notes_hz:
        t = np.linspace(0, duration_per_note, int(sr * duration_per_note))
        note = np.sin(2 * np.pi * freq * t) * 0.5
        audio_segments.append(note)

    audio = np.concatenate(audio_segments)
    audio_path = temp_dir / "legato.wav"
    sf.write(str(audio_path), audio, sr)
    return audio_path


class TestArticulationAnalysis:
    """Tests for articulation analysis with real audio"""

    @pytest.mark.asyncio
    async def test_analyze_articulation_basic(self, staccato_audio):
        """Test basic articulation analysis"""
        result = await analyze_articulation(str(staccato_audio))

        assert "legato_percentage" in result
        assert "staccato_percentage" in result
        assert "articulation_consistency" in result

        assert 0.0 <= result["legato_percentage"] <= 1.0
        assert 0.0 <= result["staccato_percentage"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_articulation_staccato(self, staccato_audio):
        """Test staccato detection"""
        result = await analyze_articulation(str(staccato_audio))

        assert result["staccato_percentage"] > result["legato_percentage"]

    @pytest.mark.asyncio
    async def test_analyze_articulation_legato(self, legato_audio):
        """Test legato detection"""
        result = await analyze_articulation(str(legato_audio))

        assert result["legato_percentage"] > result["staccato_percentage"]


    @pytest.mark.asyncio
    async def test_analyze_articulation_accent_detection(self, temp_dir):
        """A note much louder than the others must be reported as an accent.
        The old heuristic compared loudness to 1.2x the mean note DURATION
        ratio (unrelated units), flagging nearly every note."""
        import numpy as np
        import soundfile as sf

        sr = 22050
        duration = 4.0
        y = np.zeros(int(sr * duration), dtype=np.float32)
        for i in range(8):
            start = int(i * 0.5 * sr)
            end = min(start + int(0.3 * sr), len(y))
            t = np.linspace(0, (end - start) / sr, end - start)
            amp = 0.9 if i == 4 else 0.25  # one accented note
            y[start:end] = (amp * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 3)).astype(np.float32)

        path = temp_dir / "accents.wav"
        sf.write(str(path), y, sr)

        result = await analyze_articulation(str(path))

        assert "accents" in result
        assert 1 <= len(result["accents"]) <= 2, result["accents"]
        # The accent should be at ~2.0s (the loud note)
        assert any(abs(a["time"] - 2.0) < 0.3 for a in result["accents"]), result["accents"]
        for accent in result["accents"]:
            assert accent["relative_loudness"] > 1.5
