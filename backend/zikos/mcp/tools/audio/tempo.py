"""Tempo analysis module"""

from typing import Any

import librosa
import numpy as np


async def analyze_tempo(audio_path: str) -> dict[str, Any]:
    """Analyze tempo/BPM and timing consistency"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(tempo)

        if len(beats) < 2:
            return {
                "error": True,
                "error_type": "INSUFFICIENT_BEATS",
                "message": "Could not detect enough beats for tempo analysis",
            }

        beat_times = librosa.frames_to_time(beats, sr=sr)

        inter_beat_intervals = np.diff(beat_times)
        tempo_stability = float(
            1.0 - (np.std(inter_beat_intervals) / np.mean(inter_beat_intervals))
        )
        tempo_stability = float(max(0.0, min(1.0, tempo_stability)))

        is_steady = bool(tempo_stability > 0.85)

        tempo_changes = []
        if len(beat_times) > 4:
            window_size = min(8, len(beat_times) // 2)
            for i in range(0, len(beat_times) - window_size, window_size):
                window_beats = beat_times[i : i + window_size]
                window_ibis = np.diff(window_beats)
                window_tempo = 60.0 / np.mean(window_ibis)
                tempo_changes.append(
                    {
                        "time": float(beat_times[i]),
                        "bpm": float(window_tempo),
                        "confidence": 0.9,
                    }
                )

        rushing_detected = False
        dragging_detected = False
        if len(inter_beat_intervals) > 0:
            mean_ibi = np.mean(inter_beat_intervals)
            expected_ibi = 60.0 / tempo
            if mean_ibi < expected_ibi * 0.98:
                rushing_detected = True
            elif mean_ibi > expected_ibi * 1.02:
                dragging_detected = True

        return {
            "bpm": tempo,
            "confidence": 0.9,
            "is_steady": is_steady,
            "tempo_stability_score": float(tempo_stability),
            "tempo_changes": tempo_changes,
            "rushing_detected": rushing_detected,
            "dragging_detected": dragging_detected,
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
            "message": f"Tempo analysis failed: {str(e)}",
        }
