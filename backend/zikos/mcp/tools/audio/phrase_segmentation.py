"""Phrase segmentation module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_segment_phrases_tool() -> Tool:
    """Get the segment_phrases tool definition"""
    return Tool(
        name="segment_phrases",
        description="Detect musical phrase boundaries",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Detect musical phrase boundaries.

Returns: dict with phrases (list of phrase objects with start, end, type, confidence), phrase_count, average_phrase_length

Interpretation Guidelines:
- phrases: List of detected phrases with timing and type ("melodic", "quiet", "energetic")
- phrase_count: Number of distinct phrases detected
- average_phrase_length: Average duration of phrases in seconds
- confidence: >0.7 high confidence in phrase boundary, 0.5-0.7 moderate, <0.5 low
- Use to identify musical phrases for practice and analysis
- When phrase_count is low (1-2), the piece may be a single long phrase or detection missed boundaries
- When average_phrase_length varies significantly, discuss phrase structure and breathing points
- Type classification helps identify dynamic and expressive phrases
- Useful for breaking down longer pieces into manageable practice sections
- Combine with comprehensive_analysis to understand phrase-level musical structure""",
    )


async def segment_phrases(audio_path: str) -> dict[str, Any]:
    """Detect musical phrase boundaries"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        duration = len(y) / sr

        rms = librosa.feature.rms(y=y)[0]
        frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)

        rms_smooth = np.convolve(rms, np.ones(10) / 10, mode="same")

        threshold = np.mean(rms_smooth) * 0.3

        silence_mask = rms_smooth < threshold

        phrase_boundaries = []
        in_phrase = False
        phrase_start = 0.0

        min_phrase_duration = 1.0
        min_silence_duration = 0.3

        silence_start = None

        for time, is_silent in zip(frame_times, silence_mask, strict=False):
            if not in_phrase and not is_silent:
                phrase_start = time
                in_phrase = True
                silence_start = None
            elif in_phrase and is_silent:
                if silence_start is None:
                    silence_start = time
            elif in_phrase and not is_silent and silence_start is not None:
                silence_duration = time - silence_start
                if silence_duration >= min_silence_duration:
                    phrase_end = silence_start
                    phrase_duration = phrase_end - phrase_start
                    if phrase_duration >= min_phrase_duration:
                        phrase_boundaries.append({"start": phrase_start, "end": phrase_end})
                    phrase_start = time
                    silence_start = None

        if in_phrase:
            phrase_end = duration
            phrase_duration = phrase_end - phrase_start
            if phrase_duration >= min_phrase_duration:
                phrase_boundaries.append({"start": phrase_start, "end": phrase_end})

        if len(phrase_boundaries) == 0:
            return {
                "phrases": [{"start": 0.0, "end": duration, "type": "melodic", "confidence": 0.5}],
                "phrase_count": 1,
                "average_phrase_length": duration,
            }

        phrases = []
        for boundary in phrase_boundaries:
            phrase_start = boundary["start"]
            phrase_end = boundary["end"]
            phrase_duration = phrase_end - phrase_start

            segment_start = int(phrase_start * sr)
            segment_end = int(phrase_end * sr)
            segment = y[segment_start:segment_end]

            if len(segment) > 0:
                segment_rms = np.mean(librosa.feature.rms(y=segment)[0])
                energy_level = float(segment_rms / np.max(rms) if np.max(rms) > 0 else 0.5)

                phrase_type = "melodic"
                if energy_level < 0.3:
                    phrase_type = "quiet"
                elif energy_level > 0.7:
                    phrase_type = "energetic"

                confidence = min(1.0, max(0.5, energy_level + 0.3))

                phrases.append(
                    {
                        "start": float(phrase_start),
                        "end": float(phrase_end),
                        "type": phrase_type,
                        "confidence": float(confidence),
                    }
                )

        if len(phrases) == 0:
            phrases = [{"start": 0.0, "end": duration, "type": "melodic", "confidence": 0.5}]

        phrase_lengths = [
            float(p.get("end", 0.0)) - float(p.get("start", 0.0))  # type: ignore[arg-type]
            for p in phrases
        ]
        average_phrase_length = float(np.mean(phrase_lengths)) if phrase_lengths else duration

        return {
            "phrases": phrases,
            "phrase_count": len(phrases),
            "average_phrase_length": average_phrase_length,
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
            "message": f"Failed to segment phrases: {str(e)}",
        }
