"""Audio preprocessing service using FFmpeg"""

import hashlib
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import librosa
import soundfile as sf
from fastapi import UploadFile

from zikos.config import settings
from zikos.constants import UploadConstants

# Trim anything more than this many dB below the peak — balanced for instruments.
_SILENCE_TOP_DB = 30


class AudioPreprocessingService:
    """Service for audio preprocessing using FFmpeg"""

    def __init__(self):
        self.storage_path = Path(settings.audio_storage_path)
        self.cache_dir = self.storage_path / "preprocessed"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, file_path: Path, target_format: str, target_sample_rate: int) -> str:
        """Generate cache key from file path and preprocessing parameters"""
        file_stat = file_path.stat()
        key_data = f"{file_path}_{file_stat.st_mtime}_{file_stat.st_size}_{target_format}_{target_sample_rate}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str, target_format: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.{target_format}"

    @staticmethod
    def _validated_extension(filename: str | None) -> str:
        """Return the (lowercased) extension of an uploaded filename.

        The client-supplied filename is never used for pathing — only its
        extension is extracted, and only if it is on the allowlist.
        """
        if not filename:
            raise ValueError("UploadFile must have a filename")
        extension = Path(filename).suffix.lower()
        if extension not in UploadConstants.ALLOWED_AUDIO_EXTENSIONS:
            allowed = ", ".join(sorted(UploadConstants.ALLOWED_AUDIO_EXTENSIONS))
            raise ValueError(f"Unsupported file extension {extension!r}. Allowed: {allowed}")
        return extension

    async def _save_upload_file(self, upload_file: UploadFile, temp_dir: Path) -> Path:
        """Save UploadFile to a server-generated path inside temp_dir.

        The client filename is ignored for pathing (path-traversal safe);
        a unique random name is generated per request.
        """
        extension = self._validated_extension(upload_file.filename)
        temp_path: Path = temp_dir / f"{uuid.uuid4().hex}{extension}"
        content = await upload_file.read()
        temp_path.write_bytes(content)
        await upload_file.seek(0)
        return temp_path

    async def preprocess_audio(
        self,
        input_path: Path,
        target_format: str = "wav",
        target_sample_rate: int = 44100,
        channels: int = 1,
    ) -> Path:
        """Preprocess audio file using FFmpeg

        Args:
            input_path: Path to input audio file
            target_format: Target format (wav, flac, etc.)
            target_sample_rate: Target sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)

        Returns:
            Path to preprocessed audio file

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If FFmpeg processing fails
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Audio file not found: {input_path}")

        cache_key = self._get_cache_key(input_path, target_format, target_sample_rate)
        cache_path = self._get_cache_path(cache_key, target_format)

        if cache_path.exists():
            return cache_path

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg_cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-ar",
            str(target_sample_rate),
            "-ac",
            str(channels),
            "-y",
            str(cache_path),
        ]

        try:
            subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg preprocessing failed: {e.stderr if e.stderr else e.stdout}"
            ) from e
        except FileNotFoundError as e:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg: https://ffmpeg.org/download.html"
            ) from e

        if not cache_path.exists():
            raise RuntimeError(f"FFmpeg did not create output file: {cache_path}")

        self._trim_silence(cache_path)

        return cache_path

    def _trim_silence(self, audio_path: Path) -> None:
        """Trim leading and trailing silence in-place."""
        y, sr = librosa.load(str(audio_path), sr=None)
        y_trimmed, _ = librosa.effects.trim(y, top_db=_SILENCE_TOP_DB)
        sf.write(str(audio_path), y_trimmed, sr)

    async def preprocess_upload_file(
        self,
        upload_file: UploadFile,
        target_format: str = "wav",
        target_sample_rate: int = 44100,
        channels: int = 1,
    ) -> Path:
        """Preprocess uploaded audio file

        Args:
            upload_file: FastAPI UploadFile object
            target_format: Target format (wav, flac, etc.)
            target_sample_rate: Target sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)

        Returns:
            Path to preprocessed audio file
        """
        temp_root = self.storage_path / "temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        # Per-request temp dir: no collisions between concurrent uploads of
        # the same filename, and cleanup never touches attacker-chosen paths.
        temp_dir = Path(tempfile.mkdtemp(dir=temp_root))

        try:
            temp_input = await self._save_upload_file(upload_file, temp_dir)
            return await self.preprocess_audio(
                temp_input,
                target_format=target_format,
                target_sample_rate=target_sample_rate,
                channels=channels,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def clear_cache(self) -> None:
        """Clear preprocessing cache"""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    cache_file.unlink()
