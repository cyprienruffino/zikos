"""Integration tests for audio analysis tools with real librosa and soundfile

These tests use real libraries (librosa, soundfile) instead of mocks to verify
that the integration works correctly with actual library behavior.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from src.zikos.mcp.tools.audio import AudioAnalysisTools


def generate_test_audio(
    output_path: Path,
    duration: float = 2.0,
    sample_rate: int = 22050,
    frequency: float = 440.0,
    tempo_bpm: float | None = None,
) -> Path:
    """Generate a test audio file with known characteristics

    Args:
        output_path: Path to save the audio file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of sine wave in Hz (for pitch testing)
        tempo_bpm: If provided, adds percussive beats at this tempo

    Returns:
        Path to the generated audio file
    """
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples)

    audio = np.sin(2 * np.pi * frequency * t)

    if tempo_bpm:
        beat_interval = 60.0 / tempo_bpm
        beat_samples = int(beat_interval * sample_rate)
        for i in range(0, samples, beat_samples):
            if i < samples:
                audio[i : min(i + int(0.01 * sample_rate), samples)] *= 2.0

    audio = audio.astype(np.float32)
    sf.write(str(output_path), audio, sample_rate)
    return output_path


@pytest.fixture
def audio_tools():
    """Create AudioAnalysisTools instance"""
    return AudioAnalysisTools()


@pytest.fixture
def test_audio_440hz(temp_dir):
    """Generate a 2-second audio file with 440 Hz tone (A4)"""
    audio_path = temp_dir / "test_440hz.wav"
    generate_test_audio(audio_path, duration=2.0, frequency=440.0)
    return audio_path


@pytest.fixture
def test_audio_120bpm(temp_dir):
    """Generate a 4-second audio file with beats at 120 BPM"""
    audio_path = temp_dir / "test_120bpm.wav"
    generate_test_audio(audio_path, duration=4.0, frequency=440.0, tempo_bpm=120.0)
    return audio_path


@pytest.fixture
def test_audio_short(temp_dir):
    """Generate a very short audio file (< 0.5 seconds)"""
    audio_path = temp_dir / "test_short.wav"
    generate_test_audio(audio_path, duration=0.2, frequency=440.0)
    return audio_path


@pytest.fixture
def test_audio_multiple_frequencies(temp_dir):
    """Generate audio with multiple frequencies (chord-like)"""
    audio_path = temp_dir / "test_chord.wav"
    duration = 3.0
    sample_rate = 22050
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples)

    audio = (
        np.sin(2 * np.pi * 261.63 * t)
        + np.sin(2 * np.pi * 329.63 * t)  # C4
        + np.sin(2 * np.pi * 392.00 * t)  # E4  # G4
    ) / 3.0

    audio = audio.astype(np.float32)
    sf.write(str(audio_path), audio, sample_rate)
    return audio_path


@pytest.fixture
def test_audio_variable_tempo(temp_dir):
    """Generate audio with variable tempo (accelerando)"""
    audio_path = temp_dir / "test_variable_tempo.wav"
    duration = 6.0
    sample_rate = 22050
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples)

    audio = np.sin(2 * np.pi * 440.0 * t)

    beat_interval_start = 60.0 / 100.0
    beat_interval_end = 60.0 / 150.0

    for i in range(samples):
        progress = i / samples
        current_interval = beat_interval_start * (1 - progress) + beat_interval_end * progress
        if i % int(current_interval * sample_rate) < int(0.01 * sample_rate):
            audio[i] *= 2.0

    audio = audio.astype(np.float32)
    sf.write(str(audio_path), audio, sample_rate)
    return audio_path


@pytest.fixture
def test_audio_stereo(temp_dir):
    """Generate stereo audio file"""
    audio_path = temp_dir / "test_stereo.wav"
    duration = 2.0
    sample_rate = 22050
    samples = int(duration * sample_rate)
    t = np.linspace(0, duration, samples)

    left = np.sin(2 * np.pi * 440.0 * t)
    right = np.sin(2 * np.pi * 523.25 * t)
    audio = np.column_stack([left, right]).astype(np.float32)

    sf.write(str(audio_path), audio, sample_rate)
    return audio_path


class TestTempoAnalysisIntegration:
    """Integration tests for tempo analysis with real librosa"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tempo_real_audio(self, audio_tools, test_audio_120bpm):
        """Test tempo analysis with real audio file and librosa"""
        result = await audio_tools.analyze_tempo(audio_path=str(test_audio_120bpm))

        assert "error" not in result
        assert "bpm" in result
        assert isinstance(result["bpm"], int | float)
        assert result["bpm"] > 0
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
        assert "is_steady" in result
        assert isinstance(result["is_steady"], bool)
        assert "tempo_stability_score" in result
        assert 0.0 <= result["tempo_stability_score"] <= 1.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tempo_too_short(self, audio_tools, test_audio_short):
        """Test tempo analysis with audio that's too short"""
        result = await audio_tools.analyze_tempo(audio_path=str(test_audio_short))

        assert "error" in result
        assert result["error_type"] == "TOO_SHORT"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tempo_file_not_found(self, audio_tools):
        """Test tempo analysis with non-existent file"""
        result = await audio_tools.analyze_tempo(audio_path="/nonexistent/file.wav")

        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tempo_variable_tempo(self, audio_tools, test_audio_variable_tempo):
        """Test tempo analysis with variable tempo audio"""
        result = await audio_tools.analyze_tempo(audio_path=str(test_audio_variable_tempo))

        assert "error" not in result
        assert "bpm" in result
        assert "tempo_changes" in result
        assert isinstance(result["tempo_changes"], list)
        assert "is_steady" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_tempo_stability_calculation(self, audio_tools, test_audio_120bpm):
        """Test that tempo stability is calculated correctly"""
        result = await audio_tools.analyze_tempo(audio_path=str(test_audio_120bpm))

        assert "tempo_stability_score" in result
        assert 0.0 <= result["tempo_stability_score"] <= 1.0
        assert "is_steady" in result


class TestPitchDetectionIntegration:
    """Integration tests for pitch detection with real librosa"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_pitch_real_audio(self, audio_tools, test_audio_440hz):
        """Test pitch detection with real audio file and librosa"""
        result = await audio_tools.detect_pitch(audio_path=str(test_audio_440hz))

        assert "error" not in result
        assert "notes" in result
        assert isinstance(result["notes"], list)
        assert "intonation_accuracy" in result
        assert 0.0 <= result["intonation_accuracy"] <= 1.0
        assert "pitch_stability" in result
        assert 0.0 <= result["pitch_stability"] <= 1.0
        assert "detected_key" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_pitch_too_short(self, audio_tools, test_audio_short):
        """Test pitch detection with audio that's too short"""
        result = await audio_tools.detect_pitch(audio_path=str(test_audio_short))

        assert "error" in result
        assert result["error_type"] == "TOO_SHORT"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_pitch_file_not_found(self, audio_tools):
        """Test pitch detection with non-existent file"""
        result = await audio_tools.detect_pitch(audio_path="/nonexistent/file.wav")

        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_pitch_multiple_frequencies(
        self, audio_tools, test_audio_multiple_frequencies
    ):
        """Test pitch detection with chord-like audio (multiple frequencies)"""
        result = await audio_tools.detect_pitch(audio_path=str(test_audio_multiple_frequencies))

        assert "error" not in result
        assert "notes" in result
        assert isinstance(result["notes"], list)
        assert "intonation_accuracy" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_pitch_key_detection(self, audio_tools, test_audio_440hz):
        """Test that key detection works with real librosa chroma"""
        result = await audio_tools.detect_pitch(audio_path=str(test_audio_440hz))

        assert "detected_key" in result
        assert isinstance(result["detected_key"], str)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_detect_pitch_note_segmentation(self, audio_tools, test_audio_440hz):
        """Test that note segmentation works correctly"""
        result = await audio_tools.detect_pitch(audio_path=str(test_audio_440hz))

        if len(result.get("notes", [])) > 0:
            note = result["notes"][0]
            assert "start_time" in note
            assert "end_time" in note
            assert "duration" in note
            assert "pitch" in note
            assert "frequency" in note
            assert "confidence" in note


class TestRhythmAnalysisIntegration:
    """Integration tests for rhythm analysis with real librosa"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_rhythm_real_audio(self, audio_tools, test_audio_120bpm):
        """Test rhythm analysis with real audio file and librosa"""
        result = await audio_tools.analyze_rhythm(audio_path=str(test_audio_120bpm))

        assert "error" not in result
        assert "onsets" in result
        assert isinstance(result["onsets"], list)
        assert "timing_accuracy" in result
        assert 0.0 <= result["timing_accuracy"] <= 1.0
        assert "rhythmic_pattern" in result
        assert "is_on_beat" in result
        assert isinstance(result["is_on_beat"], bool)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_rhythm_too_short(self, audio_tools, test_audio_short):
        """Test rhythm analysis with audio that's too short"""
        result = await audio_tools.analyze_rhythm(audio_path=str(test_audio_short))

        assert "error" in result
        assert result["error_type"] == "TOO_SHORT"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_analyze_rhythm_file_not_found(self, audio_tools):
        """Test rhythm analysis with non-existent file"""
        result = await audio_tools.analyze_rhythm(audio_path="/nonexistent/file.wav")

        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"


class TestAudioInfoIntegration:
    """Integration tests for audio info with real soundfile"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_audio_info_real_file(self, audio_tools, test_audio_440hz):
        """Test getting audio info with real audio file and soundfile"""
        result = await audio_tools.get_audio_info(audio_path=str(test_audio_440hz))

        assert "error" not in result
        assert "duration" in result
        assert isinstance(result["duration"], int | float)
        assert result["duration"] > 0
        assert "sample_rate" in result
        assert result["sample_rate"] == 22050
        assert "channels" in result
        assert result["channels"] == 1
        assert "format" in result
        assert "file_size_bytes" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_audio_info_file_not_found(self, audio_tools):
        """Test getting audio info with non-existent file"""
        result = await audio_tools.get_audio_info(audio_path="/nonexistent/file.wav")

        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_audio_info_stereo(self, audio_tools, test_audio_stereo):
        """Test getting audio info for stereo file"""
        result = await audio_tools.get_audio_info(audio_path=str(test_audio_stereo))

        assert "error" not in result
        assert "channels" in result
        assert result["channels"] == 2
        assert "sample_rate" in result
        assert result["sample_rate"] == 22050

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_audio_info_duration_accuracy(self, audio_tools, test_audio_440hz):
        """Test that duration is accurately reported"""
        result = await audio_tools.get_audio_info(audio_path=str(test_audio_440hz))

        assert "duration" in result
        assert abs(result["duration"] - 2.0) < 0.1
