"""Groove and microtiming analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tools.analysis.audio.utils import resolve_audio_path


async def analyze_groove(audio_path: str) -> dict[str, Any]:
    """Analyze microtiming patterns and groove"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        onsets = librosa.onset.onset_detect(y=y, sr=sr)

        if len(onsets) < 4:
            return {
                "error": True,
                "error_type": "INSUFFICIENT_ONSETS",
                "message": "Not enough onsets detected for groove analysis (minimum 4 required)",
            }

        onset_times = librosa.frames_to_time(onsets, sr=sr)

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)

        if len(beat_times) < 2:
            expected_beat_interval = 60.0 / tempo if tempo > 0 else 0.5
        else:
            inter_beat_intervals = np.diff(beat_times)
            expected_beat_interval = (
                np.mean(inter_beat_intervals) if len(inter_beat_intervals) > 0 else 0.5
            )

        inter_onset_intervals = np.diff(onset_times)

        microtiming_deviations = []
        for i, onset_time in enumerate(onset_times):
            if i == 0:
                continue

            interval = onset_times[i] - onset_times[i - 1]

            if interval < expected_beat_interval * 0.1:
                continue

            expected_intervals = []
            num_beats_in_interval = int(interval / expected_beat_interval)
            if num_beats_in_interval > 0:
                for j in range(num_beats_in_interval):
                    expected_intervals.append(expected_beat_interval * (j + 1))

                if len(expected_intervals) > 0:
                    for expected_time in expected_intervals:
                        actual_time = onset_times[i - 1] + expected_time
                        deviation_ms = (onset_time - actual_time) * 1000
                        microtiming_deviations.append(deviation_ms)

        if len(microtiming_deviations) == 0:
            microtiming_deviations = [
                (onset_times[i] - onset_times[i - 1] - expected_beat_interval) * 1000
                for i in range(1, len(onset_times))
            ]

        if len(microtiming_deviations) == 0:
            return {
                "groove_type": "straight",
                "swing_ratio": 1.0,
                "microtiming_pattern": "consistent",
                "feel_score": 0.85,
                "groove_consistency": 0.90,
            }

        microtiming_std = float(np.std(microtiming_deviations))
        microtiming_mean = float(np.mean(np.abs(microtiming_deviations)))

        groove_consistency = float(1.0 / (1.0 + microtiming_std / 20.0))
        groove_consistency = max(0.0, min(1.0, groove_consistency))

        feel_score = float(1.0 / (1.0 + microtiming_mean / 15.0))
        feel_score = max(0.0, min(1.0, feel_score))

        swing_ratio = 1.0
        groove_type = "straight"
        microtiming_pattern = "consistent"

        if len(inter_onset_intervals) >= 4:
            interval_ratios = []
            for i in range(1, len(inter_onset_intervals)):
                if inter_onset_intervals[i - 1] > 0:
                    ratio = inter_onset_intervals[i] / inter_onset_intervals[i - 1]
                    if 0.5 < ratio < 2.0:
                        interval_ratios.append(ratio)

            if len(interval_ratios) > 0:
                avg_ratio = np.mean(interval_ratios)

                if avg_ratio > 1.3:
                    groove_type = "swung"
                    swing_ratio = float(avg_ratio)
                elif avg_ratio < 0.8:
                    groove_type = "reverse_swing"
                    swing_ratio = float(avg_ratio)
                else:
                    groove_type = "straight"
                    swing_ratio = 1.0

        if microtiming_std > 30:
            microtiming_pattern = "inconsistent"
        elif microtiming_std > 15:
            microtiming_pattern = "variable"
        else:
            microtiming_pattern = "consistent"

        return {
            "groove_type": groove_type,
            "swing_ratio": float(swing_ratio),
            "microtiming_pattern": microtiming_pattern,
            "feel_score": float(feel_score),
            "groove_consistency": float(groove_consistency),
            "average_microtiming_deviation_ms": float(microtiming_mean),
            "microtiming_std_ms": float(microtiming_std),
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
            "message": f"Failed to analyze groove: {str(e)}",
        }
