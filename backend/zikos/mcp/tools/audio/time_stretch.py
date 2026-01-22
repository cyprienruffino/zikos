"""Time-stretching and pitch-shifting module"""

import uuid
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf

try:
    import pyrubberband as pyrb
except ImportError:
    pyrb = None

from zikos.config import settings
from zikos.mcp.tools.audio.utils import resolve_audio_path


async def time_stretch(audio_file_id: str, rate: float) -> dict[str, Any]:
    """Time-stretch audio without changing pitch"""
    if pyrb is None:
        return {
            "error": True,
            "error_type": "DEPENDENCY_MISSING",
            "message": "pyrubberband is not installed. Install with: pip install pyrubberband",
        }

    if rate <= 0:
        return {
            "error": True,
            "error_type": "INVALID_PARAMETER",
            "message": "rate must be greater than 0",
        }

    if rate < 0.25 or rate > 4.0:
        return {
            "error": True,
            "error_type": "INVALID_PARAMETER",
            "message": "rate must be between 0.25 and 4.0",
        }

    try:
        audio_path = resolve_audio_path(audio_file_id)
        y, sr = librosa.load(str(audio_path), sr=None)

        if len(y) / sr < 0.1:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.1 seconds required)",
            }

        y_stretched = pyrb.time_stretch(y, sr, rate)

        new_audio_file_id = str(uuid.uuid4())
        storage_path = Path(settings.audio_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        output_path = storage_path / f"{new_audio_file_id}.wav"

        sf.write(str(output_path), y_stretched, sr)

        original_duration = len(y) / sr
        new_duration = len(y_stretched) / sr

        return {
            "new_audio_file_id": new_audio_file_id,
            "original_audio_file_id": audio_file_id,
            "rate": rate,
            "original_duration": original_duration,
            "new_duration": new_duration,
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
            "message": f"Failed to time-stretch audio: {str(e)}",
        }


async def pitch_shift(audio_file_id: str, semitones: float) -> dict[str, Any]:
    """Pitch-shift audio without changing tempo"""
    if pyrb is None:
        return {
            "error": True,
            "error_type": "DEPENDENCY_MISSING",
            "message": "pyrubberband is not installed. Install with: pip install pyrubberband",
        }

    if semitones < -24 or semitones > 24:
        return {
            "error": True,
            "error_type": "INVALID_PARAMETER",
            "message": "semitones must be between -24 and 24",
        }

    try:
        audio_path = resolve_audio_path(audio_file_id)
        y, sr = librosa.load(str(audio_path), sr=None)

        if len(y) / sr < 0.1:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.1 seconds required)",
            }

        y_shifted = pyrb.pitch_shift(y, sr, semitones)

        new_audio_file_id = str(uuid.uuid4())
        storage_path = Path(settings.audio_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        output_path = storage_path / f"{new_audio_file_id}.wav"

        sf.write(str(output_path), y_shifted, sr)

        duration = len(y) / sr

        return {
            "new_audio_file_id": new_audio_file_id,
            "original_audio_file_id": audio_file_id,
            "semitones": semitones,
            "duration": duration,
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
            "message": f"Failed to pitch-shift audio: {str(e)}",
        }
