"""Audio segmentation module"""

import uuid
from pathlib import Path
from typing import Any

import librosa
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tools.audio.utils import resolve_audio_path


async def segment_audio(audio_file_id: str, start_time: float, end_time: float) -> dict[str, Any]:
    """Extract segment from audio"""
    try:
        audio_path = resolve_audio_path(audio_file_id)
        y, sr = librosa.load(str(audio_path), sr=None)

        duration = len(y) / sr

        if start_time < 0:
            return {
                "error": True,
                "error_type": "INVALID_PARAMETER",
                "message": "start_time must be non-negative",
            }

        if end_time <= start_time:
            return {
                "error": True,
                "error_type": "INVALID_PARAMETER",
                "message": "end_time must be greater than start_time",
            }

        if start_time >= duration:
            return {
                "error": True,
                "error_type": "INVALID_PARAMETER",
                "message": f"start_time ({start_time:.2f}s) exceeds audio duration ({duration:.2f}s)",
            }

        end_time = min(end_time, duration)

        start_sample = int(start_time * sr)
        end_sample = int(end_time * sr)
        segment = y[start_sample:end_sample]

        segment_duration = len(segment) / sr

        if segment_duration < 0.1:
            return {
                "error": True,
                "error_type": "INVALID_PARAMETER",
                "message": "Segment duration too short (minimum 0.1 seconds)",
            }

        new_audio_file_id = str(uuid.uuid4())
        storage_path = Path(settings.audio_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        output_path = storage_path / f"{new_audio_file_id}.wav"

        sf.write(str(output_path), segment, sr)

        return {
            "new_audio_file_id": new_audio_file_id,
            "original_audio_file_id": audio_file_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration": segment_duration,
        }
    except FileNotFoundError as e:
        return {
            "error": True,
            "error_type": "FILE_NOT_FOUND",
            "message": str(e),
        }
    except Exception as e:
        return {
            "error": True,
            "error_type": "PROCESSING_FAILED",
            "message": f"Failed to segment audio: {str(e)}",
        }
