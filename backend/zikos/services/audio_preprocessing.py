"""Audio preprocessing service using FFmpeg"""

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from zikos.config import settings


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

    async def _save_upload_file(self, upload_file: UploadFile, temp_dir: Path) -> Path:
        """Save UploadFile to temporary location"""
        filename = upload_file.filename
        if not filename:
            raise ValueError("UploadFile must have a filename")
        temp_path: Path = temp_dir / filename
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

        return cache_path

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
        filename = upload_file.filename
        if not filename:
            raise ValueError("UploadFile must have a filename")
        temp_input = self.storage_path / "temp" / filename
        temp_input.parent.mkdir(parents=True, exist_ok=True)

        try:
            await self._save_upload_file(upload_file, temp_input.parent)
            return await self.preprocess_audio(
                temp_input,
                target_format=target_format,
                target_sample_rate=target_sample_rate,
                channels=channels,
            )
        finally:
            if temp_input.exists():
                temp_input.unlink()

    def clear_cache(self) -> None:
        """Clear preprocessing cache"""
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    cache_file.unlink()
