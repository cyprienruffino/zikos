"""Instrument-aware DSP: per-instrument pyin ranges and CQT chroma

The motivating bug: with the generic fmin=C1 (32.7 Hz), a 5-string bass
low-B (B0 = 30.87 Hz) is physically outside pyin's search range, so it is
either missed or reported in the wrong octave. Passing instrument="bass"
widens the floor to 25 Hz and lengthens the analysis window.
"""

import numpy as np
import pytest
import soundfile as sf

from tests.helpers.audio_synthesis import generate_bass_tone, generate_scale_audio
from zikos.constants import DEFAULT_INSTRUMENT_DSP_PROFILE, INSTRUMENT_DSP_PROFILES
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.audio.pitch import get_detect_pitch_tool
from zikos.mcp.tools.audio.utils import resolve_instrument_profile

LOW_B_HZ = 30.87  # 5-string bass low B0


@pytest.fixture
def audio_tools():
    return AudioAnalysisTools()


@pytest.fixture
def low_b_file(temp_dir):
    """2 seconds of a bass low-B (30.87 Hz) with realistic harmonics"""
    sr = 44100
    audio = generate_bass_tone(LOW_B_HZ, duration=2.0, sample_rate=sr)
    path = temp_dir / "bass_low_b.wav"
    sf.write(str(path), audio, sr)
    return path


class TestInstrumentProfileResolution:
    def test_canonical_names(self):
        for name in INSTRUMENT_DSP_PROFILES:
            canonical, profile = resolve_instrument_profile(name)
            assert canonical == name
            assert profile == INSTRUMENT_DSP_PROFILES[name]

    def test_qualified_bass_names_resolve_to_bass(self):
        for name in [
            "bass guitar",
            "Electric Bass",
            "5-string bass",
            "double bass",
            "upright bass",
        ]:
            canonical, _ = resolve_instrument_profile(name)
            assert canonical == "bass", name

    def test_bass_guitar_is_bass_not_guitar(self):
        canonical, profile = resolve_instrument_profile("bass guitar")
        assert canonical == "bass"
        assert profile.fmin_hz < LOW_B_HZ

    def test_aliases(self):
        assert resolve_instrument_profile("keyboard")[0] == "piano"
        assert resolve_instrument_profile("keys")[0] == "piano"
        assert resolve_instrument_profile("vocals")[0] == "voice"
        assert resolve_instrument_profile("singing")[0] == "voice"
        assert resolve_instrument_profile("fiddle")[0] == "violin"
        assert resolve_instrument_profile("ukulele")[0] == "guitar"

    def test_unknown_and_missing_fall_back_to_default(self):
        for value in [None, "", "   ", "kazoo", 42, ["bass"]]:
            canonical, profile = resolve_instrument_profile(value)
            assert canonical == "default", value
            assert profile == DEFAULT_INSTRUMENT_DSP_PROFILE

    def test_bass_profile_covers_low_b(self):
        _, profile = resolve_instrument_profile("bass")
        assert profile.fmin_hz < LOW_B_HZ
        # The default profile CANNOT see low-B — that's the bug being fixed
        assert DEFAULT_INSTRUMENT_DSP_PROFILE.fmin_hz > LOW_B_HZ


class TestBassPitchDetection:
    @pytest.mark.asyncio
    async def test_low_b_detected_with_bass_profile(self, audio_tools, low_b_file):
        result = await audio_tools.detect_pitch(audio_path=str(low_b_file), instrument="bass")

        assert not result.get("error"), result
        assert result["instrument_profile"] == "bass"
        assert result["notes"], "low-B should produce at least one note"
        # Every detected note should sit on the true fundamental, not a harmonic
        for note in result["notes"]:
            assert note["pitch"] == "B0", result["notes"]
            assert abs(note["frequency"] - LOW_B_HZ) < 1.5, note["frequency"]

    @pytest.mark.asyncio
    async def test_low_b_out_of_range_without_profile(self, audio_tools, low_b_file):
        """Regression guard: the default range starts at C1 (32.7 Hz), so the
        true 30.87 Hz fundamental cannot be reported without the bass profile.
        (pyin typically latches onto the 2nd harmonic an octave up instead.)"""
        result = await audio_tools.detect_pitch(audio_path=str(low_b_file))

        assert result.get("instrument_profile", "default") == "default"
        for note in result.get("notes", []):
            assert note["frequency"] >= 32.0, (
                "default profile reported a frequency below its own fmin — "
                f"got {note['frequency']}"
            )

    @pytest.mark.asyncio
    async def test_instrument_threads_through_call_tool_schema(self):
        tool = get_detect_pitch_tool()
        assert "instrument" in tool.parameters
        assert tool.required == ["audio_file_id"]

    @pytest.mark.asyncio
    async def test_unknown_instrument_still_analyzes(self, audio_tools, temp_dir):
        sr = 44100
        audio = generate_bass_tone(110.0, duration=2.0, sample_rate=sr)  # A2
        path = temp_dir / "a2.wav"
        sf.write(str(path), audio, sr)

        result = await audio_tools.detect_pitch(audio_path=str(path), instrument="theremin")

        assert not result.get("error"), result
        assert result["instrument_profile"] == "default"


class TestLowRegisterHarmony:
    @pytest.mark.asyncio
    async def test_key_detected_from_bass_register_scale(self, audio_tools, temp_dir):
        """A C major scale played an octave below the guitar's low E: STFT
        chroma smears these pitch classes; CQT chroma must resolve them."""
        notes = ["C2", "D2", "E2", "F2", "G2", "A2", "B2", "C3"]
        audio = generate_scale_audio(notes, note_duration=0.4, instrument="bass")
        path = temp_dir / "bass_scale.wav"
        sf.write(str(path), audio, 44100)

        result = await audio_tools.detect_key(audio_path=str(path))

        assert not result.get("error"), result
        # A bare scale is ambiguous between the major key and its relative minor
        assert result["key"] in ("C major", "A minor"), result

    @pytest.mark.asyncio
    async def test_chords_detected_in_low_register(self, audio_tools, temp_dir):
        """A sustained low E-minor triad (E2-G2-B2) should be identified"""
        sr = 44100
        chord = sum(
            generate_bass_tone(float(f), duration=3.0, sample_rate=sr)
            for f in (82.41, 98.00, 123.47)
        )
        chord = chord / np.abs(chord).max() * 0.8
        path = temp_dir / "low_em.wav"
        sf.write(str(path), chord, sr)

        result = await audio_tools.detect_chords(audio_path=str(path))

        assert not result.get("error"), result
        assert "Em" in result["progression"], result["progression"]
