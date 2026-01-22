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
from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_time_stretch_tool() -> Tool:
    """Get the time_stretch tool definition"""
    return Tool(
        name="time_stretch",
        description="Time-stretch audio without changing pitch (slow down or speed up)",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
            "rate": {
                "type": "number",
                "description": "Stretch rate (0.25-4.0). 1.0 = no change, 0.5 = half speed, 2.0 = double speed",
            },
        },
        required=["audio_file_id", "rate"],
        detailed_description="""Time-stretch audio without changing pitch (slow down or speed up).

Returns: dict with new_audio_file_id, original_audio_file_id, rate, original_duration, new_duration

Interpretation Guidelines:
- rate: 0.25-0.75 slow down (useful for learning complex passages), 0.75-1.25 normal range, 1.25-2.0 speed up (useful for practice), 2.0-4.0 extreme speed up
- Use slow rates (0.5-0.75) when students need to hear details or practice difficult passages
- Use fast rates (1.25-1.5) to challenge students or demonstrate how a piece should sound at tempo
- The new audio file can be used with other analysis tools or played back to the student
- Quality may degrade at extreme rates (<0.5 or >2.0), especially with complex audio
- Useful for creating practice loops at different tempos without changing pitch""",
    )


def get_pitch_shift_tool() -> Tool:
    """Get the pitch_shift tool definition"""
    return Tool(
        name="pitch_shift",
        description="Pitch-shift audio without changing tempo (transpose)",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
            "semitones": {
                "type": "number",
                "description": "Number of semitones to shift (-24 to 24). Positive = higher, negative = lower",
            },
        },
        required=["audio_file_id", "semitones"],
        detailed_description="""Pitch-shift audio without changing tempo (transpose).

Returns: dict with new_audio_file_id, original_audio_file_id, semitones, duration

Interpretation Guidelines:
- semitones: -12 to -1 lower (useful for transposing to comfortable keys), 0 no change, 1 to 12 higher
- Use to transpose recordings to match student's vocal range or instrument tuning
- Common shifts: -2 or -3 semitones for lower voices, +2 or +3 for higher voices
- Quality is best within ±12 semitones (one octave)
- Useful for demonstrating how a piece sounds in different keys
- Can help students practice in their comfortable range before moving to original key
- The new audio file can be used with other analysis tools or played back to the student""",
    )


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
