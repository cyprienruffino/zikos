"""Rhythm and timing analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory

# Finer hop gives ~2.9ms resolution at 44100 Hz, preventing the 11.6ms quantization
# artifact where on-beat notes appear as "minor" deviations instead of being filtered out.
_HOP_LENGTH = 128


def get_analyze_rhythm_tool() -> Tool:
    """Get the analyze_rhythm tool definition"""
    return Tool(
        name="analyze_rhythm",
        description="Analyze rhythm and timing accuracy. Returns: onsets, timing_accuracy (0.0-1.0), inter_onset_interval_cv, beat_deviations, average_deviation_ms, rushing_tendency, dragging_tendency",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze rhythm and timing accuracy.

Returns: dict with onsets, timing_accuracy (0.0-1.0), inter_onset_interval_cv, beat_deviations, average_deviation_ms, rushing_tendency, dragging_tendency

Interpretation Guidelines:
- timing_accuracy: >0.90 excellent, 0.80-0.90 good, 0.70-0.80 needs work, <0.70 poor
- average_deviation_ms: <10ms excellent, 10-20ms good, 20-50ms needs work, >50ms poor
- rushing_tendency/dragging_tendency: <0.15 low, 0.15-0.30 moderate, >0.30 high
- inter_onset_interval_cv (coefficient of variation): <0.1 very regular, 0.1-0.3 moderate variation, >0.3 irregular
- When timing_accuracy < 0.80 AND rushing_tendency > 0.15, consider suggesting metronome practice
- When deviations are clustered, identify patterns (e.g., "rushing on the downbeat")""",
    )


def calculate_timing_accuracy(onset_times: np.ndarray, beat_times: np.ndarray) -> float:
    """Calculate timing accuracy score (0.0-1.0) from time arrays (seconds)"""
    if len(onset_times) == 0 or len(beat_times) == 0:
        return 0.0

    deviations = []
    for onset_time in onset_times:
        closest_beat_idx = np.argmin(np.abs(beat_times - onset_time))
        deviation_ms = (onset_time - beat_times[closest_beat_idx]) * 1000
        deviations.append(abs(deviation_ms))

    avg_deviation_ms = float(np.mean(deviations))

    if avg_deviation_ms < 10:
        return 1.0
    elif avg_deviation_ms < 20:
        return 0.9
    elif avg_deviation_ms < 50:
        return float(0.8 - (avg_deviation_ms - 20) / 300)
    else:
        return float(max(0.0, 0.7 - (avg_deviation_ms - 50) / 500))


async def analyze_rhythm(audio_path: str) -> dict[str, Any]:
    """Analyze rhythm and timing"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        onset_strength = librosa.onset.onset_strength(y=y, sr=sr, hop_length=_HOP_LENGTH)
        onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=_HOP_LENGTH)

        if len(onsets) == 0:
            return {
                "error": True,
                "error_type": "NO_ONSETS_DETECTED",
                "message": "Could not detect any onsets in audio",
            }

        # Ensure we don't index out of bounds
        valid_onsets = onsets[onsets < len(onset_strength)]
        if len(valid_onsets) == 0:
            return {
                "error": True,
                "error_type": "NO_ONSETS_DETECTED",
                "message": "Could not detect any valid onsets in audio",
            }

        onset_times = librosa.frames_to_time(valid_onsets, sr=sr, hop_length=_HOP_LENGTH)
        onset_strengths = onset_strength[valid_onsets]

        onsets_list = [
            {
                "time": float(time),
                "confidence": float(strength),
            }
            for time, strength in zip(onset_times, onset_strengths, strict=False)
        ]

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=_HOP_LENGTH)

        timing_accuracy = 0.87
        beat_deviations = []
        rushing_tendency = 0.0
        dragging_tendency = 0.0
        average_deviation_ms = 0.0

        if len(beats) > 0 and len(onsets) > 0:
            beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=_HOP_LENGTH)
            timing_accuracy = calculate_timing_accuracy(onset_times, beat_times)

            deviations = []
            for onset_time in onset_times:
                closest_beat_idx = np.argmin(np.abs(beat_times - onset_time))
                deviation_ms = (onset_time - beat_times[closest_beat_idx]) * 1000
                deviations.append(deviation_ms)

                if abs(deviation_ms) > 10:
                    beat_deviations.append(
                        {
                            "time": float(onset_time),
                            "deviation_ms": float(deviation_ms),
                        }
                    )

            if len(deviations) > 0:
                average_deviation_ms = np.mean(deviations)
                rushing_count = sum(1 for d in deviations if d < -10)
                dragging_count = sum(1 for d in deviations if d > 10)
                rushing_tendency = rushing_count / len(deviations)
                dragging_tendency = dragging_count / len(deviations)

        inter_onset_interval_cv = 0.0
        if len(onset_times) >= 4:
            inter_onset_intervals = np.diff(onset_times)
            mean_ioi = np.mean(inter_onset_intervals)
            if mean_ioi > 0:
                inter_onset_interval_cv = float(np.std(inter_onset_intervals) / mean_ioi)

        return {
            "onsets": onsets_list,
            "timing_accuracy": float(timing_accuracy),
            "inter_onset_interval_cv": inter_onset_interval_cv,
            "beat_deviations": beat_deviations,
            "average_deviation_ms": float(average_deviation_ms),
            "rushing_tendency": float(rushing_tendency),
            "dragging_tendency": float(dragging_tendency),
        }
    except FileNotFoundError:
        return {
            "error": True,
            "error_type": "FILE_NOT_FOUND",
            "message": f"Audio file not found: {audio_path}",
        }
    except Exception as e:
        return {
            "error": True,
            "error_type": "PROCESSING_FAILED",
            "message": f"Rhythm analysis failed: {str(e)}",
        }
