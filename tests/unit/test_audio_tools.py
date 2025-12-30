"""Tests for audio analysis tools"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools


@pytest.fixture
def audio_tools():
    """Create AudioAnalysisTools instance"""
    return AudioAnalysisTools()


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file with real audio data"""
    from tests.helpers.audio_synthesis import create_test_audio_file

    audio_path = temp_dir / "test_audio.wav"
    create_test_audio_file(audio_path, audio_type="rhythm", duration=2.0, tempo=120.0)
    return audio_path


class TestTempoAnalysis:
    """Tests for tempo analysis"""

    @pytest.mark.asyncio
    async def test_analyze_tempo_basic(self, audio_tools, sample_audio_file):
        """Test basic tempo analysis with real librosa"""
        result = await audio_tools.analyze_tempo(audio_path=str(sample_audio_file))

        assert "bpm" in result
        assert result["bpm"] > 0
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
        assert "is_steady" in result
        assert isinstance(result["is_steady"], bool)
        assert "tempo_stability_score" in result
        assert 0.0 <= result["tempo_stability_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_tempo_with_changes(self, audio_tools, temp_dir):
        """Test tempo analysis with tempo changes using real audio"""
        from tests.helpers.audio_synthesis import generate_rhythmic_pattern, save_audio_file

        # Create audio with variable tempo (accelerando)
        duration = 6.0
        sample_rate = 22050
        audio = generate_rhythmic_pattern(100.0, duration, sample_rate)
        # Add accelerando effect
        for i in range(len(audio)):
            if i % 10000 == 0:
                audio[i] *= 1.5  # Simulate tempo increase

        audio_file = temp_dir / "variable_tempo.wav"
        save_audio_file(audio, audio_file, sample_rate)

        result = await audio_tools.analyze_tempo(audio_path=str(audio_file))

        assert "tempo_changes" in result
        assert isinstance(result["tempo_changes"], list)

    @pytest.mark.asyncio
    async def test_analyze_tempo_rushing_dragging(self, audio_tools, temp_dir):
        """Test detection of rushing/dragging with real audio"""
        from tests.helpers.audio_synthesis import generate_rhythmic_pattern, save_audio_file

        # Create audio with slightly rushed tempo (beats come early)
        duration = 4.0
        sample_rate = 22050
        audio = generate_rhythmic_pattern(125.0, duration, sample_rate)

        audio_file = temp_dir / "rushed_tempo.wav"
        save_audio_file(audio, audio_file, sample_rate)

        result = await audio_tools.analyze_tempo(audio_path=str(audio_file))

        assert "rushing_detected" in result or "dragging_detected" in result
        # At least one should be present
        assert isinstance(result.get("rushing_detected", False), bool) or isinstance(
            result.get("dragging_detected", False), bool
        )

    @pytest.mark.asyncio
    async def test_analyze_tempo_file_not_found(self, audio_tools):
        """Test error handling for missing file"""
        result = await audio_tools.analyze_tempo(audio_file_id="nonexistent")
        assert "error" in result
        assert result["error_type"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_analyze_tempo_audio_too_short(self, audio_tools, temp_dir):
        """Test error handling for too short audio"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        # Create very short audio file (< 0.5 seconds)
        short_audio = temp_dir / "short_audio.wav"
        create_test_audio_file(short_audio, audio_type="single_note", duration=0.2)

        result = await audio_tools.analyze_tempo(audio_path=str(short_audio))

        # Should return error structure
        assert "error" in result or "bpm" in result

    @pytest.mark.asyncio
    async def test_analyze_tempo_insufficient_beats(self, audio_tools, temp_dir):
        """Test tempo analysis with insufficient beats using real audio"""
        # Create audio with very few beats (single note, no rhythm)
        from tests.helpers.audio_synthesis import create_test_audio_file

        single_note_audio = temp_dir / "single_note.wav"
        create_test_audio_file(single_note_audio, audio_type="single_note", duration=0.8)

        result = await audio_tools.analyze_tempo(audio_path=str(single_note_audio))

        # May return error or minimal analysis depending on implementation
        assert "error" in result or "bpm" in result

    @pytest.mark.asyncio
    async def test_analyze_tempo_no_tempo_changes(self, audio_tools, sample_audio_file):
        """Test tempo analysis with steady tempo using real audio"""
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

        with (
            patch("librosa.load") as mock_load,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
            patch("librosa.feature.chroma_stft") as mock_chroma,
        ):
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

        with (
            patch("librosa.load") as mock_load,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
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
        from zikos.mcp.tools.analysis.audio.pitch import frequency_to_cents, frequency_to_note

        note, octave = frequency_to_note(0.0)
        assert note == "C"
        assert octave == 0

        cents = frequency_to_cents(0.0, 440.0)
        assert cents == 0.0

    @pytest.mark.asyncio
    async def test_detect_pitch_basic(self, audio_tools, temp_dir):
        """Test basic pitch detection with real librosa"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        audio_file = temp_dir / "pitch_test.wav"
        create_test_audio_file(audio_file, audio_type="single_note", duration=2.0, frequency=440.0)

        result = await audio_tools.detect_pitch(audio_path=str(audio_file))

        assert "notes" in result
        assert isinstance(result["notes"], list)
        assert "intonation_accuracy" in result
        assert 0.0 <= result["intonation_accuracy"] <= 1.0
        assert "pitch_stability" in result
        assert 0.0 <= result["pitch_stability"] <= 1.0

    @pytest.mark.asyncio
    async def test_detect_pitch_note_segmentation(self, audio_tools, temp_dir):
        """Test note segmentation with real audio"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        audio_file = temp_dir / "scale_test.wav"
        create_test_audio_file(audio_file, audio_type="scale", duration=3.0)

        result = await audio_tools.detect_pitch(audio_path=str(audio_file))

        assert "notes" in result
        if len(result["notes"]) > 0:
            note = result["notes"][0]
            assert "start_time" in note
            assert "end_time" in note or "duration" in note
            assert "pitch" in note
            assert "frequency" in note
            assert "confidence" in note

    @pytest.mark.asyncio
    async def test_detect_pitch_intonation_accuracy(self, audio_tools, temp_dir):
        """Test intonation accuracy calculation with real audio"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        audio_file = temp_dir / "perfect_pitch.wav"
        create_test_audio_file(audio_file, audio_type="single_note", duration=2.0, frequency=440.0)

        result = await audio_tools.detect_pitch(audio_path=str(audio_file))

        assert "intonation_accuracy" in result
        assert 0.0 <= result["intonation_accuracy"] <= 1.0

    @pytest.mark.asyncio
    async def test_detect_pitch_sharp_flat_tendency(self, audio_tools, temp_dir):
        """Test detection of sharp/flat tendencies with real audio"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        # Create audio slightly sharp (445 Hz instead of 440 Hz for A4)
        audio_file = temp_dir / "sharp_pitch.wav"
        create_test_audio_file(audio_file, audio_type="single_note", duration=2.0, frequency=445.0)

        result = await audio_tools.detect_pitch(audio_path=str(audio_file))

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

        with (
            patch("librosa.load") as mock_load,
            patch("librosa.onset.onset_strength") as mock_strength,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
            mock_load.return_value = (audio, sr)
            mock_strength.return_value = np.array([0.9] * 100)  # Small array
            mock_onset.return_value = np.array([200, 300])  # Out of bounds

            result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

            assert "error" in result
            assert result["error_type"] == "NO_ONSETS_DETECTED"

    @pytest.mark.asyncio
    async def test_analyze_rhythm_basic(self, audio_tools, sample_audio_file):
        """Test basic rhythm analysis with real librosa"""
        result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

        assert "onsets" in result
        assert isinstance(result["onsets"], list)
        assert "timing_accuracy" in result
        assert 0.0 <= result["timing_accuracy"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_rhythm_onsets(self, audio_tools, sample_audio_file):
        """Test onset detection with real librosa"""
        result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

        assert "onsets" in result
        if len(result["onsets"]) > 0:
            onset = result["onsets"][0]
            assert "time" in onset
            assert "confidence" in onset
            assert 0.0 <= onset["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_rhythm_timing_accuracy(self, audio_tools, sample_audio_file):
        """Test timing accuracy calculation with real audio"""
        result = await audio_tools.analyze_rhythm(audio_path=str(sample_audio_file))

        assert "timing_accuracy" in result
        assert 0.0 <= result["timing_accuracy"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_rhythm_beat_deviations(
        self, audio_tools, sample_audio_file, mock_audio_data
    ):
        """Test beat deviation detection"""
        audio, sr = mock_audio_data

        with (
            patch("librosa.load") as mock_load,
            patch("librosa.onset.onset_strength") as mock_strength,
            patch("librosa.onset.onset_detect") as mock_onset,
            patch("librosa.beat.beat_track") as mock_beat,
        ):
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

        with (
            patch("librosa.load") as mock_load,
            patch("librosa.onset.onset_strength") as mock_strength,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
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
        """Test getting audio file information with real soundfile"""
        result = await audio_tools.get_audio_info(audio_path=str(sample_audio_file))

        assert "duration" in result
        assert result["duration"] > 0
        assert "sample_rate" in result
        assert result["sample_rate"] > 0
        assert "channels" in result
        assert "format" in result

    @pytest.mark.asyncio
    async def test_get_audio_info_via_call_tool(self, audio_tools, sample_audio_file):
        """Test get_audio_info via call_tool (MCP tool exposure) with real soundfile"""
        result = await audio_tools.call_tool("get_audio_info", audio_path=str(sample_audio_file))

        assert "duration" in result
        assert result["duration"] > 0
        assert "sample_rate" in result
        assert result["sample_rate"] > 0
        assert "channels" in result
        assert "format" in result
        assert "file_size_bytes" in result


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
        from zikos.mcp.tools.analysis.audio.utils import resolve_audio_path

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
        from zikos.mcp.tools.analysis.audio.utils import resolve_audio_path

        with patch.object(settings, "audio_storage_path", temp_dir):
            with pytest.raises(FileNotFoundError):
                resolve_audio_path("nonexistent")

    def test_create_error_response(self):
        """Test create_error_response"""
        from zikos.mcp.tools.analysis.audio.utils import create_error_response

        result = create_error_response("TEST_ERROR", "Test message")
        assert result["error"] is True
        assert result["error_type"] == "TEST_ERROR"
        assert result["message"] == "Test message"
        assert "details" not in result

    def test_create_error_response_with_details(self):
        """Test create_error_response with details"""
        from zikos.mcp.tools.analysis.audio.utils import create_error_response

        details = {"key": "value"}
        result = create_error_response("TEST_ERROR", "Test message", details)
        assert result["error"] is True
        assert result["details"] == details

    def test_validate_audio_duration_valid(self):
        """Test validate_audio_duration with valid duration"""
        from zikos.mcp.tools.analysis.audio.utils import validate_audio_duration

        audio = np.array([0.0] * 22050)  # 1 second at 22050 Hz
        is_valid, message = validate_audio_duration(audio, 22050, min_duration=0.5)
        assert is_valid is True
        assert message is None

    def test_validate_audio_duration_too_short(self):
        """Test validate_audio_duration with too short audio"""
        from zikos.mcp.tools.analysis.audio.utils import validate_audio_duration

        audio = np.array([0.0] * 5000)  # ~0.23 seconds at 22050 Hz
        is_valid, message = validate_audio_duration(audio, 22050, min_duration=0.5)
        assert is_valid is False
        assert message is not None
        assert "too short" in message.lower()


class TestComparisonTools:
    """Tests for audio comparison tools"""

    @pytest.mark.asyncio
    async def test_compare_audio_overall(self, audio_tools, temp_dir):
        """Test compare_audio with overall comparison"""
        audio_file_id_1 = "test_audio_1"
        audio_file_id_2 = "test_audio_2"
        file_1 = temp_dir / f"{audio_file_id_1}.wav"
        file_2 = temp_dir / f"{audio_file_id_2}.wav"
        file_1.touch()
        file_2.touch()

        with (
            patch.object(settings, "audio_storage_path", str(temp_dir)),
            patch("librosa.load") as mock_load,
            patch("librosa.beat.beat_track") as mock_beat,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
            audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100))
            sr = 22050
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))
            mock_pyin.return_value = (
                np.array([440.0] * 100),
                np.array([True] * 100),
                np.array([0.9] * 100),
            )
            mock_onset.return_value = np.array([0, 5512, 11025])

            result = await audio_tools.call_tool(
                "compare_audio",
                audio_file_id_1=audio_file_id_1,
                audio_file_id_2=audio_file_id_2,
                comparison_type="overall",
            )

            assert "comparison_type" in result
            assert result["comparison_type"] == "overall"
            assert "similarity_score" in result
            assert "differences" in result
            assert "improvements" in result
            assert "regressions" in result

    @pytest.mark.asyncio
    async def test_compare_audio_tempo(self, audio_tools, temp_dir):
        """Test compare_audio with tempo comparison"""
        audio_file_id_1 = "test_audio_1"
        audio_file_id_2 = "test_audio_2"
        file_1 = temp_dir / f"{audio_file_id_1}.wav"
        file_2 = temp_dir / f"{audio_file_id_2}.wav"
        file_1.touch()
        file_2.touch()

        with (
            patch.object(settings, "audio_storage_path", str(temp_dir)),
            patch("librosa.load") as mock_load,
            patch("librosa.beat.beat_track") as mock_beat,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
            audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100))
            sr = 22050
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))
            mock_pyin.return_value = (
                np.array([440.0] * 100),
                np.array([True] * 100),
                np.array([0.9] * 100),
            )
            mock_onset.return_value = np.array([0, 5512, 11025])

            result = await audio_tools.call_tool(
                "compare_audio",
                audio_file_id_1=audio_file_id_1,
                audio_file_id_2=audio_file_id_2,
                comparison_type="tempo",
            )

            assert result["comparison_type"] == "tempo"
            assert "differences" in result
            assert "tempo" in result["differences"]

    @pytest.mark.asyncio
    async def test_compare_audio_missing_files(self, audio_tools):
        """Test compare_audio with missing files"""
        result = await audio_tools.call_tool(
            "compare_audio",
            audio_file_id_1="nonexistent_1",
            audio_file_id_2="nonexistent_2",
        )

        assert "error" in result
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_compare_to_reference_scale(self, audio_tools, temp_dir):
        """Test compare_to_reference with scale"""
        audio_file_id = "test_audio"
        file_path = temp_dir / f"{audio_file_id}.wav"
        file_path.touch()

        with (
            patch.object(settings, "audio_storage_path", str(temp_dir)),
            patch("librosa.load") as mock_load,
            patch("librosa.beat.beat_track") as mock_beat,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
            patch("librosa.feature.chroma_stft") as mock_chroma,
        ):
            audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100))
            sr = 22050
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))
            mock_pyin.return_value = (
                np.array([440.0] * 100),
                np.array([True] * 100),
                np.array([0.9] * 100),
            )
            mock_onset.return_value = np.array([0, 5512, 11025])
            chroma_array = np.zeros((12, 100))
            chroma_array[0, :] = 1.0
            mock_chroma.return_value = chroma_array

            result = await audio_tools.call_tool(
                "compare_to_reference",
                audio_file_id=audio_file_id,
                reference_type="scale",
                reference_params={"scale": "C major", "tempo": 120},
            )

            assert "reference_type" in result
            assert result["reference_type"] == "scale"
            assert "scale" in result
            assert result["scale"] == "C major"
            assert "comparison" in result
            assert "errors" in result

    @pytest.mark.asyncio
    async def test_compare_to_reference_midi_file(self, audio_tools, temp_dir):
        """Test compare_to_reference with MIDI file"""
        audio_file_id = "test_audio"
        midi_file_id = "test_midi"
        file_path = temp_dir / f"{audio_file_id}.wav"
        midi_path = temp_dir / f"{midi_file_id}.mid"
        file_path.touch()
        midi_path.touch()

        with (
            patch.object(settings, "audio_storage_path", str(temp_dir)),
            patch("librosa.load") as mock_load,
            patch("librosa.beat.beat_track") as mock_beat,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
            patch("zikos.mcp.tools.processing.midi.MidiTools") as mock_midi_tools_class,
        ):
            audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100))
            sr = 22050
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))
            mock_pyin.return_value = (
                np.array([440.0] * 100),
                np.array([True] * 100),
                np.array([0.9] * 100),
            )
            mock_onset.return_value = np.array([0, 5512, 11025])

            mock_midi_tools = MagicMock()
            mock_midi_tools.storage_path = temp_dir
            mock_midi_tools_class.return_value = mock_midi_tools

            from unittest.mock import MagicMock as Mock

            mock_score = Mock()
            mock_score.metronomeMarkBoundaries.return_value = [(None, None, Mock(number=120))]
            with patch("music21.midi.translate.midiFilePathToStream", return_value=mock_score):
                result = await audio_tools.call_tool(
                    "compare_to_reference",
                    audio_file_id=audio_file_id,
                    reference_type="midi_file",
                    reference_params={"midi_file_id": midi_file_id},
                )

                assert "reference_type" in result
                assert result["reference_type"] == "midi_file"
                assert "comparison" in result

    @pytest.mark.asyncio
    async def test_compare_to_reference_missing_midi_file_id(self, audio_tools, temp_dir):
        """Test compare_to_reference with missing midi_file_id"""
        audio_file_id = "test_audio"
        file_path = temp_dir / f"{audio_file_id}.wav"
        file_path.touch()

        with (
            patch.object(settings, "audio_storage_path", str(temp_dir)),
            patch("librosa.load") as mock_load,
            patch("librosa.beat.beat_track") as mock_beat,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
            audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100))
            sr = 22050
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))
            mock_pyin.return_value = (
                np.array([440.0] * 100),
                np.array([True] * 100),
                np.array([0.9] * 100),
            )
            mock_onset.return_value = np.array([0, 5512, 11025])

            result = await audio_tools.call_tool(
                "compare_to_reference",
                audio_file_id=audio_file_id,
                reference_type="midi_file",
                reference_params={},
            )

            assert "error" in result
            assert result["error"] is True

    @pytest.mark.asyncio
    async def test_compare_to_reference_invalid_type(self, audio_tools, temp_dir):
        """Test compare_to_reference with invalid reference type"""
        audio_file_id = "test_audio"
        file_path = temp_dir / f"{audio_file_id}.wav"
        file_path.touch()

        with (
            patch.object(settings, "audio_storage_path", str(temp_dir)),
            patch("librosa.load") as mock_load,
            patch("librosa.beat.beat_track") as mock_beat,
            patch("librosa.pyin") as mock_pyin,
            patch("librosa.onset.onset_detect") as mock_onset,
        ):
            audio = np.sin(2 * np.pi * 440 * np.linspace(0, 2, 44100))
            sr = 22050
            mock_load.return_value = (audio, sr)
            mock_beat.return_value = (120.0, np.array([0, 5512, 11025]))
            mock_pyin.return_value = (
                np.array([440.0] * 100),
                np.array([True] * 100),
                np.array([0.9] * 100),
            )
            mock_onset.return_value = np.array([0, 5512, 11025])

            result = await audio_tools.call_tool(
                "compare_to_reference",
                audio_file_id=audio_file_id,
                reference_type="invalid_type",
                reference_params={},
            )

            assert "error" in result
            assert result["error"] is True


class TestToolSchemas:
    """Tests for tool schema generation"""

    def test_get_tool_schemas(self, audio_tools):
        """Test get_tool_schemas returns correct structure"""
        schemas = audio_tools.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 18

        tool_names = [s["function"]["name"] for s in schemas]
        assert "analyze_tempo" in tool_names
        assert "detect_pitch" in tool_names
        assert "analyze_rhythm" in tool_names
        assert "compare_audio" in tool_names
        assert "compare_to_reference" in tool_names

        for schema in schemas:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
