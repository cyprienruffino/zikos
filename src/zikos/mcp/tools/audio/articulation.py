"""Articulation analysis module"""

from typing import Any

import librosa
import numpy as np


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
        inter_onset_intervals = np.diff(onset_times)

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

        np.mean(note_durations)
        np.mean(inter_onset_intervals)

        staccato_threshold = 0.4
        legato_threshold = 0.7

        staccato_count = sum(1 for d in note_durations if d < staccato_threshold)
        legato_count = sum(1 for d in note_durations if d > legato_threshold)

        total_notes = len(note_durations)
        staccato_percentage = staccato_count / total_notes if total_notes > 0 else 0.0
        legato_percentage = legato_count / total_notes if total_notes > 0 else 0.0

        articulation_types = []
        if staccato_percentage > 0.3:
            articulation_types.append("staccato")
        if legato_percentage > 0.3:
            articulation_types.append("legato")
        if not articulation_types:
            articulation_types.append("mixed")

        duration_std = float(np.std(note_durations))
        articulation_consistency = float(1.0 / (1.0 + duration_std))
        articulation_consistency = max(0.0, min(1.0, articulation_consistency))

        return {
            "articulation_types": articulation_types,
            "legato_percentage": float(legato_percentage),
            "staccato_percentage": float(staccato_percentage),
            "articulation_consistency": articulation_consistency,
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
