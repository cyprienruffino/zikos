"""Audio segmentation module"""

import uuid
from pathlib import Path
from typing import Any

import librosa
import soundfile as sf

from zikos.config import settings
from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_segment_audio_tool() -> Tool:
    """Get the segment_audio tool definition"""
    return Tool(
        name="segment_audio",
        description="Extract a segment from audio file",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
            "start_time": {
                "type": "number",
                "description": "Start time in seconds",
            },
            "end_time": {"type": "number", "description": "End time in seconds"},
        },
        required=["audio_file_id", "start_time", "end_time"],
        detailed_description="""Extract a segment from audio file.

Returns: dict with new_audio_file_id, original_audio_file_id, start_time, end_time, duration

Interpretation Guidelines:
- Use to isolate specific sections for focused analysis or practice
- Minimum segment duration: 0.1 seconds
- The new audio file can be used with any other analysis tool
- Useful for extracting difficult passages, specific phrases, or sections that need work
- When analyzing a long recording, segment it first to focus on problem areas
- The new_audio_file_id can be used for playback, further analysis, or comparison
- Combine with phrase_segmentation to extract musical phrases automatically""",
    )


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
