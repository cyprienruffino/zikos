"""Utility functions for audio analysis"""

from pathlib import Path
from typing import Any

from zikos.config import settings


def resolve_audio_path(audio_file_id: str) -> Path:
    """Resolve audio_file_id to file path"""
    storage_path = Path(settings.audio_storage_path)
    file_path = storage_path / f"{audio_file_id}.wav"

    if not file_path.exists():
        raise FileNotFoundError(f"Audio file {audio_file_id} not found")

    return file_path


def create_error_response(
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create structured error response"""
    response = {
        "error": True,
        "error_type": error_type,
        "message": message,
    }
    if details:
        response["details"] = details
    return response


def validate_audio_duration(
    audio: Any, sample_rate: int, min_duration: float = 0.5
) -> tuple[bool, str | None]:
    """Validate audio duration"""
    duration = len(audio) / sample_rate
    if duration < min_duration:
        return (
            False,
            f"Audio is too short (minimum {min_duration} seconds required, got {duration:.2f})",
        )
    return True, None
