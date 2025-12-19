"""Tests for audio analysis tools"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from zikos.config import settings
from zikos.mcp.tools.audio import AudioAnalysisTools


@pytest.fixture
def audio_tools():
    """Create AudioAnalysisTools instance"""
    return AudioAnalysisTools()


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file path"""
    audio_path = temp_dir / "test_audio.wav"
    audio_path.touch()
    return audio_path


@pytest.fixture
def mock_audio_data():
    """Mock audio data (samples, sample_rate)"""
    # Generate 2 seconds of audio at 22050 Hz
    duration = 2.0
    sr = 22050
    samples = int(duration * sr)
    # Simple sine wave at 440 Hz (A4)
    t = np.linspace(0, duration, samples)
    audio = np.sin(2 * np.pi * 440 * t)
    return audio, sr


class TestTempoAnalysis:
    """Tests for tempo analysis"""

    @pytest.mark.asyncio
    async def test_analyze_tempo_basic(self, audio_tools, sample_audio_file, mock_audio_data):
        """Test basic tempo analysis"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.beat.beat_track") as mock_beat:
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025, 16537]))

            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            assert "bpm" in result
            assert result["bpm"] == 120.0
            assert "confidence" in result
            assert 0.0 <= result["confidence"] <= 1.0
            assert "is_steady" in result
            assert isinstance(result["is_steady"], bool)
            assert "tempo_stability_score" in result
            assert 0.0 <= result["tempo_stability_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_tempo_with_changes(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test tempo analysis with tempo changes"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.beat.beat_track") as mock_beat:
            mock_load.return_value = (audio, sr)
            # Return enough beats for tempo change detection (need at least 8 beats)
            mock_beat.return_value = (
                120.0,
                np.array([0, 5512, 11025, 16537, 22050, 27562, 33075, 38587]),
            )

            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            assert "tempo_changes" in result
            assert isinstance(result["tempo_changes"], list)

    @pytest.mark.asyncio
    async def test_analyze_tempo_rushing_dragging(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test detection of rushing/dragging"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.beat.beat_track") as mock_beat:
            mock_load.return_value = (audio, sr)
            # Simulate rushing (beats come early)
            mock_beat.return_value = (125.0, np.array([0, 5280, 10560]))

            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            assert "rushing_detected" in result
            assert "dragging_detected" in result
            assert isinstance(result["rushing_detected"], bool)
            assert isinstance(result["dragging_detected"], bool)

    @pytest.mark.asyncio
    async def test_analyze_tempo_file_not_found(self, audio_tools):
        """Test error handling for missing file"""
        result = await audio_tools.analyze_tempo(audio_file_id="nonexistent")
        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_analyze_tempo_audio_too_short(self, audio_tools, sample_audio_file):
        """Test error handling for too short audio"""
        # Create very short audio
        audio = np.array([0.0] * 100)  # Less than 0.01 seconds at 22050 Hz
        sr = 22050

        with patch("librosa.load") as mock_load:
            mock_load.return_value = (audio, sr)

            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            # Should return error structure
            assert "error" in result or "bpm" in result

    @pytest.mark.asyncio
    async def test_analyze_tempo_insufficient_beats(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test tempo analysis with insufficient beats"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.beat.beat_track") as mock_beat:
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0]))  # Only one beat

            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            assert "error" in result
            assert result["error_type"] == "INSUFFICIENT_BEATS"

    @pytest.mark.asyncio
    async def test_analyze_tempo_no_tempo_changes(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test tempo analysis with no tempo changes (few beats)"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.beat.beat_track") as mock_beat:
            mock_load.return_value = (audio, sr)
            # Only 3 beats - not enough for tempo change detection
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))

            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            assert "tempo_changes" in result
            assert isinstance(result["tempo_changes"], list)


class TestPitchDetection:
    """Tests for pitch detection"""

    @pytest.mark.asyncio
    async def test_detect_pitch_no_pitch_detected(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test pitch detection when no pitch is detected"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin:
            mock_load.return_value = (audio, sr)
            # No voiced frames
            f0 = np.array([np.nan] * 100)
            voiced_flag = np.array([False] * 100)
            voiced_prob = np.array([0.1] * 100)
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "error" in result
            assert result["error_type"] == "NO_PITCH_DETECTED"

    @pytest.mark.asyncio
    async def test_detect_pitch_key_detection_exception(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test pitch detection when key detection fails"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin, patch(
            "librosa.onset.onset_detect"
        ) as mock_onset, patch("librosa.feature.chroma_stft") as mock_chroma:
            mock_load.return_value = (audio, sr)
            f0 = np.array([440.0] * 100)
            voiced_flag = np.array([True] * 100)
            voiced_prob = np.array([0.95] * 100)
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)
            mock_onset.return_value = np.array([0, 11025])
            mock_chroma.side_effect = Exception("Chroma failed")

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "detected_key" in result
            assert result["detected_key"] == "unknown"

    @pytest.mark.asyncio
    async def test_detect_pitch_no_notes_segmented(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test pitch detection when no notes are segmented"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin, patch(
            "librosa.onset.onset_detect"
        ) as mock_onset:
            mock_load.return_value = (audio, sr)
            f0 = np.array([440.0] * 100)
            voiced_flag = np.array([True] * 100)
            voiced_prob = np.array([0.95] * 100)
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)
            mock_onset.return_value = np.array([])  # No onsets

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "notes" in result
            assert len(result["notes"]) == 0
            assert result["detected_key"] == "unknown"

    @pytest.mark.asyncio
    async def test_detect_pitch_zero_frequency_handling(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test pitch detection with zero frequencies"""
        from zikos.mcp.tools.audio.pitch import frequency_to_cents, frequency_to_note

        note, octave = frequency_to_note(0.0)
        assert note == "C"
        assert octave == 0

        cents = frequency_to_cents(0.0, 440.0)
        assert cents == 0.0

    @pytest.mark.asyncio
    async def test_detect_pitch_basic(self, audio_tools, sample_audio_file, mock_audio_data):
        """Test basic pitch detection"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin:
            mock_load.return_value = (audio, sr)
            # Mock PYIN output: f0, voiced_flag, voiced_prob
            f0 = np.array([440.0, 440.1, 440.0, 440.2])
            voiced_flag = np.array([True, True, True, True])
            voiced_prob = np.array([0.95, 0.94, 0.96, 0.93])
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "notes" in result
            assert isinstance(result["notes"], list)
            assert "intonation_accuracy" in result
            assert 0.0 <= result["intonation_accuracy"] <= 1.0
            assert "pitch_stability" in result
            assert 0.0 <= result["pitch_stability"] <= 1.0

    @pytest.mark.asyncio
    async def test_detect_pitch_note_segmentation(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test note segmentation"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin, patch(
            "librosa.onset.onset_detect"
        ) as mock_onset:
            mock_load.return_value = (audio, sr)
            f0 = np.array([440.0] * 100)
            voiced_flag = np.array([True] * 100)
            voiced_prob = np.array([0.95] * 100)
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)
            mock_onset.return_value = np.array([0, 11025, 22050])

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "notes" in result
            if len(result["notes"]) > 0:
                note = result["notes"][0]
                assert "start_time" in note
                assert "end_time" in note or "duration" in note
                assert "pitch" in note
                assert "frequency" in note
                assert "confidence" in note

    @pytest.mark.asyncio
    async def test_detect_pitch_intonation_accuracy(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test intonation accuracy calculation"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin:
            mock_load.return_value = (audio, sr)
            # Perfect A4 (440 Hz)
            f0 = np.array([440.0] * 100)
            voiced_flag = np.array([True] * 100)
            voiced_prob = np.array([0.95] * 100)
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "intonation_accuracy" in result
            # Perfect pitch should give high accuracy
            assert result["intonation_accuracy"] > 0.8

    @pytest.mark.asyncio
    async def test_detect_pitch_sharp_flat_tendency(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test detection of sharp/flat tendencies"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch("librosa.pyin") as mock_pyin:
            mock_load.return_value = (audio, sr)
            # Slightly sharp (445 Hz instead of 440 Hz for A4)
            f0 = np.array([445.0] * 100)
            voiced_flag = np.array([True] * 100)
            voiced_prob = np.array([0.95] * 100)
            mock_pyin.return_value = (f0, voiced_flag, voiced_prob)

            result = await audio_tools.detect_pitch(audio_path=str(sample_audio_file))

            assert "sharp_tendency" in result or "flat_tendency" in result
            if "sharp_tendency" in result:
                assert 0.0 <= result["sharp_tendency"] <= 1.0


class TestRhythmAnalysis:
    """Tests for rhythm analysis"""

    @pytest.mark.asyncio
    async def test_analyze_rhythm_no_valid_onsets(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test rhythm analysis when onsets are out of bounds"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch(
            "librosa.onset.onset_strength"
        ) as mock_strength, patch("librosa.onset.onset_detect") as mock_onset:
            mock_load.return_value = (audio, sr)
            mock_strength.return_value = np.array([0.9] * 100)  # Small array
            mock_onset.return_value = np.array([200, 300])  # Out of bounds

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "error" in result
            assert result["error_type"] == "NO_ONSETS_DETECTED"

    @pytest.mark.asyncio
    async def test_analyze_rhythm_basic(self, audio_tools, sample_audio_file, mock_audio_data):
        """Test basic rhythm analysis"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch(
            "librosa.onset.onset_strength"
        ) as mock_strength, patch("librosa.onset.onset_detect") as mock_onset:
            mock_load.return_value = (audio, sr)
            # Create onset_strength array large enough for the onsets
            mock_strength.return_value = np.array([0.9] * 20000)
            mock_onset.return_value = np.array([0, 5512, 11025, 16537])

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "onsets" in result
            assert isinstance(result["onsets"], list)
            assert "timing_accuracy" in result
            assert 0.0 <= result["timing_accuracy"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_rhythm_onsets(self, audio_tools, sample_audio_file, mock_audio_data):
        """Test onset detection"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch(
            "librosa.onset.onset_strength"
        ) as mock_strength, patch("librosa.onset.onset_detect") as mock_onset:
            mock_load.return_value = (audio, sr)
            onset_times = np.array([0.0, 0.5, 1.0, 1.5])
            onset_frames = (onset_times * sr).astype(int)
            mock_strength.return_value = np.array([0.9] * 20000)
            mock_onset.return_value = onset_frames

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "onsets" in result
            assert len(result["onsets"]) > 0
            onset = result["onsets"][0]
            assert "time" in onset
            assert "confidence" in onset
            assert 0.0 <= onset["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_rhythm_timing_accuracy(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test timing accuracy calculation"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch(
            "librosa.onset.onset_strength"
        ) as mock_strength, patch("librosa.onset.onset_detect") as mock_onset, patch(
            "librosa.beat.beat_track"
        ) as mock_beat:
            mock_load.return_value = (audio, sr)
            # Perfect quarter notes at 120 BPM (0.5s intervals)
            perfect_onsets = np.array([0, 11025, 22050, 33075])
            mock_strength.return_value = np.array([0.9] * 20000)
            mock_onset.return_value = perfect_onsets
            mock_beat.return_value = (120.0, perfect_onsets)

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "timing_accuracy" in result
            # Perfect timing should give high accuracy
            assert result["timing_accuracy"] > 0.85

    @pytest.mark.asyncio
    async def test_analyze_rhythm_beat_deviations(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test beat deviation detection"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch(
            "librosa.onset.onset_strength"
        ) as mock_strength, patch("librosa.onset.onset_detect") as mock_onset, patch(
            "librosa.beat.beat_track"
        ) as mock_beat:
            mock_load.return_value = (audio, sr)
            # Onsets slightly early (rushing)
            onsets = np.array([0, 10800, 21600, 32400])  # 20ms early each time
            mock_strength.return_value = np.array([0.9] * 20000)
            mock_onset.return_value = onsets
            # Expected beats
            expected_beats = np.array([0, 11025, 22050, 33075])
            mock_beat.return_value = (120.0, expected_beats)

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "beat_deviations" in result
            assert isinstance(result["beat_deviations"], list)
            if len(result["beat_deviations"]) > 0:
                deviation = result["beat_deviations"][0]
                assert "time" in deviation
                assert "deviation_ms" in deviation
                assert "severity" in deviation

    @pytest.mark.asyncio
    async def test_analyze_rhythm_rushing_dragging(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test rushing/dragging tendency detection"""
        audio, sr = mock_audio_data

        with patch("librosa.load") as mock_load, patch(
            "librosa.onset.onset_strength"
        ) as mock_strength, patch("librosa.onset.onset_detect") as mock_onset:
            mock_load.return_value = (audio, sr)
            mock_strength.return_value = np.array([0.9] * 20000)
            mock_onset.return_value = np.array([0, 5512, 11025])

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "rushing_tendency" in result or "average_deviation_ms" in result
            assert "dragging_tendency" in result or "average_deviation_ms" in result


class TestAudioInfo:
    """Tests for audio info tool"""

    @pytest.mark.asyncio
    async def test_get_audio_info(self, audio_tools, sample_audio_file):
        """Test getting audio file information"""
        with patch("soundfile.info") as mock_info:
            mock_info_obj = MagicMock()
            mock_info_obj.duration = 10.5
            mock_info_obj.samplerate = 44100
            mock_info_obj.channels = 2
            mock_info_obj.format = "WAV"
            mock_info_obj.frames = 463050
            mock_info.return_value = mock_info_obj

            result = await audio_tools.get_audio_info(audio_path=str(sample_audio_file))

            assert "duration" in result
            assert result["duration"] == 10.5
            assert "sample_rate" in result
            assert result["sample_rate"] == 44100
            assert "channels" in result
            assert result["channels"] == 2
            assert "format" in result


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_error_handling_invalid_file(self, audio_tools):
        """Test error handling for invalid file"""
        result = await audio_tools.analyze_tempo(audio_file_id="nonexistent")
        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_error_handling_audio_too_short(self, audio_tools, sample_audio_file):
        """Test error handling for too short audio"""
        # Very short audio (less than 0.5 seconds)
        audio = np.array([0.0] * 5000)  # ~0.23 seconds at 22050 Hz
        sr = 22050

        with patch("librosa.load") as mock_load:
            mock_load.return_value = (audio, sr)

            # Should handle gracefully, either return error or minimal analysis
            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            # Should either have error flag or valid (but limited) results
            assert "error" in result or "bpm" in result

    @pytest.mark.asyncio
    async def test_error_handling_processing_failure(self, audio_tools, sample_audio_file):
        """Test error handling for processing failures"""
        with patch("librosa.load") as mock_load:
            mock_load.side_effect = Exception("Processing failed")

            # Should return structured error
            result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

            assert "error" in result
            assert "error_type" in result
            assert "message" in result

    @pytest.mark.asyncio
    async def test_error_handling_missing_parameter(self, audio_tools):
        """Test error handling for missing parameters"""
        result = await audio_tools.analyze_tempo()
        assert "error" in result
        assert result["error_type"] == "MISSING_PARAMETER"

    @pytest.mark.asyncio
    async def test_error_handling_unknown_tool(self, audio_tools, sample_audio_file):
        """Test error handling for unknown tool"""
        result = await audio_tools.call_tool("unknown_tool", audio_path=str(sample_audio_file))
        assert "error" in result
        assert result["error_type"] == "UNKNOWN_TOOL"

    @pytest.mark.asyncio
    async def test_get_audio_info_missing_parameter(self, audio_tools):
        """Test get_audio_info with missing parameters"""
        result = await audio_tools.get_audio_info()
        assert "error" in result
        assert result["error_type"] == "MISSING_PARAMETER"

    @pytest.mark.asyncio
    async def test_get_audio_info_file_not_found(self, audio_tools):
        """Test get_audio_info with non-existent file"""
        result = await audio_tools.get_audio_info(audio_file_id="nonexistent")
        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_audio_info_processing_error(self, audio_tools, sample_audio_file):
        """Test get_audio_info with processing error"""
        with patch("soundfile.info") as mock_info:
            mock_info.side_effect = Exception("Processing failed")
            result = await audio_tools.get_audio_info(audio_path=str(sample_audio_file))
            assert "error" in result
            assert result["error_type"] == "PROCESSING_FAILED"


class TestUtils:
    """Tests for utility functions"""

    def test_resolve_audio_path(self, temp_dir):
        """Test resolve_audio_path"""
        from zikos.config import settings
        from zikos.mcp.tools.audio.utils import resolve_audio_path

        # Create a test file
        test_file = temp_dir / "test_audio.wav"
        test_file.touch()

        # Mock settings to use temp_dir
        with patch.object(settings, "audio_storage_path", temp_dir):
            result = resolve_audio_path("test_audio")
            assert result == test_file

    def test_resolve_audio_path_not_found(self, temp_dir):
        """Test resolve_audio_path with non-existent file"""
        from zikos.config import settings
        from zikos.mcp.tools.audio.utils import resolve_audio_path

        with patch.object(settings, "audio_storage_path", temp_dir):
            with pytest.raises(FileNotFoundError):
                resolve_audio_path("nonexistent")

    def test_create_error_response(self):
        """Test create_error_response"""
        from zikos.mcp.tools.audio.utils import create_error_response

        result = create_error_response("TEST_ERROR", "Test message")
        assert result["error"] is True
        assert result["error_type"] == "TEST_ERROR"
        assert result["message"] == "Test message"
        assert "details" not in result

    def test_create_error_response_with_details(self):
        """Test create_error_response with details"""
        from zikos.mcp.tools.audio.utils import create_error_response

        details = {"key": "value"}
        result = create_error_response("TEST_ERROR", "Test message", details)
        assert result["error"] is True
        assert result["details"] == details

    def test_validate_audio_duration_valid(self):
        """Test validate_audio_duration with valid duration"""
        from zikos.mcp.tools.audio.utils import validate_audio_duration

        audio = np.array([0.0] * 22050)  # 1 second at 22050 Hz
        is_valid, message = validate_audio_duration(audio, 22050, min_duration=0.5)
        assert is_valid is True
        assert message is None

    def test_validate_audio_duration_too_short(self):
        """Test validate_audio_duration with too short audio"""
        from zikos.mcp.tools.audio.utils import validate_audio_duration

        audio = np.array([0.0] * 5000)  # ~0.23 seconds at 22050 Hz
        is_valid, message = validate_audio_duration(audio, 22050, min_duration=0.5)
        assert is_valid is False
        assert message is not None
        assert "too short" in message.lower()


class TestToolSchemas:
    """Tests for tool schema generation"""

    def test_get_tool_schemas(self, audio_tools):
        """Test get_tool_schemas returns correct structure"""
        schemas = audio_tools.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 8

        tool_names = [s["function"]["name"] for s in schemas]
        assert "analyze_tempo" in tool_names
        assert "detect_pitch" in tool_names
        assert "analyze_rhythm" in tool_names

        for schema in schemas:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
