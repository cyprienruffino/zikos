"""Articulation analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory


def get_analyze_articulation_tool() -> Tool:
    """Get the analyze_articulation tool definition"""
    return Tool(
        name="analyze_articulation",
        description="Analyze articulation. Returns: legato_percentage, staccato_percentage, articulation_consistency (0.0-1.0), accents",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze articulation types (staccato, legato, etc.).

Returns: dict with legato_percentage (0.0-1.0), staccato_percentage (0.0-1.0), articulation_consistency (0.0-1.0), accents (list of {time, intensity, relative_loudness})

Interpretation Guidelines:
- legato_percentage/staccato_percentage: fraction of notes sustained (>70% of the inter-onset gap) vs clipped short (<40%)
- articulation_consistency: >0.85 very uniform note lengths, <0.7 inconsistent articulation
- accents: notes noticeably louder than the median note (relative_loudness is the ratio to the median note peak)
- High staccato_percentage on a legato passage (or vice versa) suggests articulation practice
- Clustered accents can indicate intended phrasing; scattered accents may indicate uneven touch""",
    )


async def analyze_articulation(audio_path: str) -> dict[str, Any]:
    """Analyze articulation types (staccato, legato, etc.)"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        onsets = librosa.onset.onset_detect(y=y, sr=sr)

        if len(onsets) < 2:
            return {
                "error": True,
                "error_type": "INSUFFICIENT_ONSETS",
                "message": "Not enough onsets for articulation analysis",
            }

        onset_times = librosa.frames_to_time(onsets, sr=sr)

        note_durations = []
        for i in range(len(onsets) - 1):
            onset_start = onset_times[i]
            onset_end = onset_times[i + 1]

            start_sample = int(onset_start * sr)
            end_sample = int(onset_end * sr)
            segment = y[start_sample:end_sample]

            if len(segment) > 0:
                max_amplitude = np.max(np.abs(segment))
                threshold = max_amplitude * 0.1

                above_threshold = np.abs(segment) > threshold
                if np.any(above_threshold):
                    note_samples = np.where(above_threshold)[0]
                    note_duration_samples = note_samples[-1] - note_samples[0] + 1
                    note_duration_ratio = note_duration_samples / len(segment)
                else:
                    note_duration_ratio = 0.0
                note_durations.append(note_duration_ratio)
            else:
                note_durations.append(0.0)

        if len(note_durations) == 0:
            return {
                "error": True,
                "error_type": "PROCESSING_FAILED",
                "message": "Could not calculate note durations",
            }

        staccato_threshold = 0.4
        legato_threshold = 0.7

        staccato_count = sum(1 for d in note_durations if d < staccato_threshold)
        legato_count = sum(1 for d in note_durations if d > legato_threshold)

        total_notes = len(note_durations)
        staccato_percentage = staccato_count / total_notes if total_notes > 0 else 0.0
        legato_percentage = legato_count / total_notes if total_notes > 0 else 0.0

        duration_std = float(np.std(note_durations))
        articulation_consistency = float(1.0 / (1.0 + duration_std))
        articulation_consistency = max(0.0, min(1.0, articulation_consistency))

        # Accents: notes noticeably louder than the typical (median) note.
        # (The old heuristic compared a loudness ratio to 1.2x the mean note
        # DURATION ratio - two unrelated quantities.)
        note_peaks = []
        for i in range(len(onset_times) - 1):
            start_sample = int(onset_times[i] * sr)
            end_sample = int(onset_times[i + 1] * sr)
            segment = y[start_sample:end_sample]
            note_peaks.append(float(np.max(np.abs(segment))) if len(segment) > 0 else 0.0)

        accents = []
        positive_peaks = [p for p in note_peaks if p > 0]
        median_peak = float(np.median(positive_peaks)) if positive_peaks else 0.0
        if median_peak > 0:
            accent_ratio_threshold = 1.5
            for i, peak in enumerate(note_peaks):
                relative_loudness = peak / median_peak
                if relative_loudness > accent_ratio_threshold:
                    accents.append(
                        {
                            "time": float(onset_times[i]),
                            "intensity": float(min(1.0, relative_loudness / 2.0)),
                            "relative_loudness": float(relative_loudness),
                        }
                    )

        return {
            "legato_percentage": float(legato_percentage),
            "staccato_percentage": float(staccato_percentage),
            "articulation_consistency": articulation_consistency,
            "accents": accents,
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
            "message": f"Articulation analysis failed: {str(e)}",
        }
