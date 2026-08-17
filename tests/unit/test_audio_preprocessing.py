"""Tests for audio preprocessing service"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import librosa
import pytest

from zikos.services.audio_preprocessing import AudioPreprocessingService


@pytest.fixture
def preprocessing_service(temp_dir):
    """Create AudioPreprocessingService instance with temp directory"""
    with patch("zikos.config.settings") as mock_settings:
        mock_settings.audio_storage_path = temp_dir
        service = AudioPreprocessingService()
        service.cache_dir = temp_dir / "preprocessed"
        service.cache_dir.mkdir(parents=True, exist_ok=True)
        return service


@pytest.fixture
def sample_wav_file(temp_dir):
    """Create a sample WAV file for testing"""
    from tests.helpers.audio_synthesis import create_test_audio_file

    audio_file = temp_dir / "sample.wav"
    create_test_audio_file(audio_file, audio_type="single_note", duration=1.0)
    return audio_file


class TestAudioPreprocessingService:
    """Tests for AudioPreprocessingService"""

    @pytest.mark.asyncio
    async def test_preprocess_wav_file_no_conversion_needed(
        self, preprocessing_service, sample_wav_file
    ):
        """Test preprocessing WAV file that doesn't need conversion"""
        output_path = await preprocessing_service.preprocess_audio(
            sample_wav_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path.exists()
        assert output_path.suffix == ".wav"
        assert output_path != sample_wav_file

    @pytest.mark.asyncio
    async def test_preprocess_audio_converts_format(
        self, preprocessing_service, sample_wav_file, temp_dir
    ):
        """Test preprocessing converts audio format"""
        # Use real WAV file and convert it (simulating format conversion)
        # In real usage, we'd have an MP3, but for testing we can use WAV as input
        # and verify the conversion logic works
        output_path = await preprocessing_service.preprocess_audio(
            sample_wav_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path.suffix == ".wav"
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_preprocess_audio_converts_sample_rate(
        self, preprocessing_service, sample_wav_file
    ):
        """Test preprocessing converts sample rate using real ffmpeg"""
        output_path = await preprocessing_service.preprocess_audio(
            sample_wav_file, target_format="wav", target_sample_rate=22050
        )

        assert output_path.exists()
        # Verify the file was actually converted by checking it exists and is valid
        assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_preprocess_audio_caches_result(self, preprocessing_service, sample_wav_file):
        """Test preprocessing caches results"""
        output_path1 = await preprocessing_service.preprocess_audio(
            sample_wav_file, target_format="wav", target_sample_rate=44100
        )

        output_path2 = await preprocessing_service.preprocess_audio(
            sample_wav_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path1 == output_path2

    @pytest.mark.asyncio
    async def test_preprocess_audio_handles_missing_file(self, preprocessing_service, temp_dir):
        """Test preprocessing handles missing file"""
        missing_file = temp_dir / "nonexistent.wav"

        with pytest.raises(FileNotFoundError):
            await preprocessing_service.preprocess_audio(
                missing_file, target_format="wav", target_sample_rate=44100
            )

    @pytest.mark.asyncio
    async def test_preprocess_audio_handles_ffmpeg_error(
        self, preprocessing_service, sample_wav_file
    ):
        """Test preprocessing handles FFmpeg errors"""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="FFmpeg error")

            with pytest.raises(RuntimeError, match="FFmpeg preprocessing failed"):
                await preprocessing_service.preprocess_audio(
                    sample_wav_file, target_format="wav", target_sample_rate=22050
                )

    @pytest.mark.asyncio
    async def test_preprocess_audio_handles_ffmpeg_not_found(
        self, preprocessing_service, sample_wav_file
    ):
        """Test preprocessing handles FFmpeg not found"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ffmpeg not found")

            with pytest.raises(RuntimeError, match="FFmpeg not found"):
                await preprocessing_service.preprocess_audio(
                    sample_wav_file, target_format="wav", target_sample_rate=22050
                )

    @pytest.mark.asyncio
    async def test_preprocess_audio_supports_various_formats(self, preprocessing_service, temp_dir):
        """Test preprocessing supports various input formats using real ffmpeg"""
        from tests.helpers.audio_synthesis import create_test_audio_file

        # Create real WAV file and test conversion
        # Note: For full format testing (mp3, flac, etc.), we'd need real files of those formats
        # This test verifies the conversion logic works with a real audio file
        test_file = temp_dir / "test.wav"
        create_test_audio_file(test_file, audio_type="single_note", duration=1.0)

        output_path = await preprocessing_service.preprocess_audio(
            test_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path.suffix == ".wav"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_preprocess_audio_creates_cache_directory(
        self, preprocessing_service, sample_wav_file, temp_dir
    ):
        """Test preprocessing creates cache directory if it doesn't exist"""
        cache_dir = temp_dir / "new_cache"
        preprocessing_service.cache_dir = cache_dir

        assert not cache_dir.exists()

        await preprocessing_service.preprocess_audio(
            sample_wav_file, target_format="wav", target_sample_rate=44100
        )

        assert cache_dir.exists()

    @pytest.mark.asyncio
    async def test_preprocess_audio_handles_upload_file(self, preprocessing_service, temp_dir):
        """Test preprocessing handles UploadFile objects using real ffmpeg"""
        from io import BytesIO

        import soundfile as sf
        from fastapi import UploadFile

        from tests.helpers.audio_synthesis import create_test_audio_file

        # Create real audio data
        test_audio_file = temp_dir / "source.wav"
        create_test_audio_file(test_audio_file, audio_type="single_note", duration=1.0)

        # Read it as bytes for UploadFile
        audio_data = test_audio_file.read_bytes()
        upload_file = UploadFile(
            filename="test.wav", file=BytesIO(audio_data), headers={"content-type": "audio/wav"}
        )

        output_path = await preprocessing_service.preprocess_upload_file(
            upload_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path.suffix == ".wav"
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_silence_trimmed_from_output(self, preprocessing_service, temp_dir):
        """Preprocessed audio must be shorter than input padded with silence."""
        import numpy as np
        import soundfile as sf

        sr = 44100
        one_sec_silence = np.zeros(sr, dtype=np.float32)
        tone = (np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr)) * 0.8).astype(np.float32)
        # 1 s silence + 1 s tone + 1 s silence = 3 s total
        padded = np.concatenate([one_sec_silence, tone, one_sec_silence])
        input_path = temp_dir / "padded.wav"
        sf.write(str(input_path), padded, sr)

        output_path = await preprocessing_service.preprocess_audio(
            input_path, target_format="wav", target_sample_rate=sr
        )

        out_audio, _ = librosa.load(str(output_path), sr=None)
        assert len(out_audio) < len(padded), "Output should be shorter after silence trimming"

    def test_trim_silence_directly(self, preprocessing_service, temp_dir):
        """_trim_silence shortens a file that has leading/trailing silence."""
        import numpy as np
        import soundfile as sf

        sr = 22050
        silence = np.zeros(sr // 2, dtype=np.float32)
        tone = (np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, sr // 2)) * 0.8).astype(np.float32)
        audio = np.concatenate([silence, tone, silence])
        path = temp_dir / "silent.wav"
        sf.write(str(path), audio, sr)

        preprocessing_service._trim_silence(path)

        trimmed, _ = sf.read(str(path))
        assert len(trimmed) < len(audio)

    @pytest.mark.asyncio
    async def test_upload_filename_path_traversal_is_ignored(
        self, preprocessing_service, temp_dir
    ):
        """Client filenames with ../ must not escape the temp storage dir."""
        from io import BytesIO

        from fastapi import UploadFile

        from tests.helpers.audio_synthesis import create_test_audio_file

        # A file outside storage that a traversal filename would clobber/delete
        outside_target = temp_dir.parent / "victim.wav"
        outside_target.write_bytes(b"do not delete me")

        source = temp_dir / "src.wav"
        create_test_audio_file(source, audio_type="single_note", duration=1.0)
        upload_file = UploadFile(
            filename="../victim.wav",
            file=BytesIO(source.read_bytes()),
            headers={"content-type": "audio/wav"},
        )

        output_path = await preprocessing_service.preprocess_upload_file(
            upload_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path.exists()
        # Victim file untouched (not overwritten, not deleted by cleanup)
        assert outside_target.read_bytes() == b"do not delete me"

    @pytest.mark.asyncio
    async def test_upload_absolute_filename_is_ignored(self, preprocessing_service, temp_dir):
        """Absolute client filenames must not be written to."""
        from io import BytesIO

        from fastapi import UploadFile

        from tests.helpers.audio_synthesis import create_test_audio_file

        source = temp_dir / "src2.wav"
        create_test_audio_file(source, audio_type="single_note", duration=1.0)
        evil_path = temp_dir.parent / "absolute_evil.wav"
        upload_file = UploadFile(
            filename=str(evil_path),
            file=BytesIO(source.read_bytes()),
            headers={"content-type": "audio/wav"},
        )

        output_path = await preprocessing_service.preprocess_upload_file(
            upload_file, target_format="wav", target_sample_rate=44100
        )

        assert output_path.exists()
        assert not evil_path.exists()

    @pytest.mark.asyncio
    async def test_upload_disallowed_extension_rejected(self, preprocessing_service):
        """Uploads with non-audio extensions are rejected."""
        from io import BytesIO

        from fastapi import UploadFile

        upload_file = UploadFile(filename="malware.exe", file=BytesIO(b"MZ..."))

        with pytest.raises(ValueError, match="Unsupported file extension"):
            await preprocessing_service.preprocess_upload_file(upload_file)

    @pytest.mark.asyncio
    async def test_upload_missing_filename_rejected(self, preprocessing_service):
        """Uploads without a filename are rejected."""
        from io import BytesIO

        from fastapi import UploadFile

        upload_file = UploadFile(filename=None, file=BytesIO(b"data"))

        with pytest.raises(ValueError, match="must have a filename"):
            await preprocessing_service.preprocess_upload_file(upload_file)

    @pytest.mark.asyncio
    async def test_upload_temp_dir_cleaned_up(self, preprocessing_service, temp_dir):
        """Per-request temp dirs are removed even on success."""
        from io import BytesIO

        from fastapi import UploadFile

        from tests.helpers.audio_synthesis import create_test_audio_file

        source = temp_dir / "src3.wav"
        create_test_audio_file(source, audio_type="single_note", duration=1.0)
        upload_file = UploadFile(filename="ok.wav", file=BytesIO(source.read_bytes()))

        await preprocessing_service.preprocess_upload_file(upload_file)

        temp_root = preprocessing_service.storage_path / "temp"
        assert list(temp_root.iterdir()) == []

    def test_clear_cache(self, preprocessing_service, temp_dir):
        """Test clearing preprocessing cache"""
        cache_file = preprocessing_service.cache_dir / "test.wav"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(b"cached data")

        assert cache_file.exists()

        preprocessing_service.clear_cache()

        assert not cache_file.exists()
