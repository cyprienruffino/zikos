"""Tests for articulation analysis with real audio"""

import numpy as np
import pytest
import soundfile as sf

from src.zikos.mcp.tools.audio.articulation import analyze_articulation


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

        assert "articulation_types" in result
        assert "legato_percentage" in result
        assert "staccato_percentage" in result
        assert "articulation_consistency" in result

        assert isinstance(result["articulation_types"], list)
        assert 0.0 <= result["legato_percentage"] <= 1.0
        assert 0.0 <= result["staccato_percentage"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_articulation_staccato(self, staccato_audio):
        """Test staccato detection"""
        result = await analyze_articulation(str(staccato_audio))

        assert result["staccato_percentage"] > result["legato_percentage"]
        assert "staccato" in result["articulation_types"]

    @pytest.mark.asyncio
    async def test_analyze_articulation_legato(self, legato_audio):
        """Test legato detection"""
        result = await analyze_articulation(str(legato_audio))

        assert result["legato_percentage"] > result["staccato_percentage"]
        assert "legato" in result["articulation_types"]
