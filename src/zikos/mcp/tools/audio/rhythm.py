"""Rhythm and timing analysis module"""

from typing import Any

import librosa
import numpy as np


def calculate_timing_accuracy(
    onsets: np.ndarray, expected_beats: np.ndarray, sample_rate: int
) -> float:
    """Calculate timing accuracy score (0.0-1.0)"""
    if len(onsets) == 0 or len(expected_beats) == 0:
        return 0.0

    onset_times = librosa.frames_to_time(onsets, sr=sample_rate)
    beat_times = librosa.frames_to_time(expected_beats, sr=sample_rate)

    deviations = []
    for onset_time in onset_times:
        closest_beat_idx = np.argmin(np.abs(beat_times - onset_time))
        deviation_ms = (onset_time - beat_times[closest_beat_idx]) * 1000
        deviations.append(abs(deviation_ms))

    if len(deviations) == 0:
        return 0.0

    avg_deviation_ms = float(np.mean(deviations))

    if avg_deviation_ms < 10:
        return 1.0
    elif avg_deviation_ms < 20:
        return 0.9
    elif avg_deviation_ms < 50:
        return float(0.8 - (avg_deviation_ms - 20) / 300)
    else:
        return float(max(0.0, 0.7 - (avg_deviation_ms - 50) / 500))


def classify_deviation_severity(deviation_ms: float) -> str:
    """Classify deviation severity"""
    abs_dev = abs(deviation_ms)
    if abs_dev < 10:
        return "negligible"
    elif abs_dev < 20:
        return "minor"
    elif abs_dev < 50:
        return "moderate"
    else:
        return "major"


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

        onset_strength = librosa.onset.onset_strength(y=y, sr=sr)
        onsets = librosa.onset.onset_detect(y=y, sr=sr)

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

        onset_times = librosa.frames_to_time(valid_onsets, sr=sr)
        onset_strengths = onset_strength[valid_onsets]

        onsets_list = [
            {
                "time": float(time),
                "confidence": float(strength),
            }
            for time, strength in zip(onset_times, onset_strengths, strict=False)
        ]

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        timing_accuracy = 0.87
        beat_deviations = []
        rushing_tendency = 0.0
        dragging_tendency = 0.0
        average_deviation_ms = 0.0

        if len(beats) > 0 and len(onsets) > 0:
            timing_accuracy = calculate_timing_accuracy(onsets, beats, int(sr))

            beat_times = librosa.frames_to_time(beats, sr=sr)

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
                            "severity": classify_deviation_severity(deviation_ms),
                        }
                    )

            if len(deviations) > 0:
                average_deviation_ms = np.mean(deviations)
                rushing_count = sum(1 for d in deviations if d < -10)
                dragging_count = sum(1 for d in deviations if d > 10)
                rushing_tendency = rushing_count / len(deviations)
                dragging_tendency = dragging_count / len(deviations)

        is_on_beat = timing_accuracy > 0.80

        rhythmic_pattern = "unknown"
        if len(onsets) >= 4:
            inter_onset_intervals = np.diff(onset_times)
            if np.std(inter_onset_intervals) / np.mean(inter_onset_intervals) < 0.1:
                rhythmic_pattern = "regular"

        return {
            "onsets": onsets_list,
            "timing_accuracy": float(timing_accuracy),
            "rhythmic_pattern": rhythmic_pattern,
            "is_on_beat": is_on_beat,
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
