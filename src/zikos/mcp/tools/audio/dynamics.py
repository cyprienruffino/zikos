"""Dynamics and amplitude analysis module"""

from typing import Any

import librosa
import numpy as np
import soundfile as sf


async def analyze_dynamics(audio_path: str) -> dict[str, Any]:
    """Analyze amplitude and dynamic range"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        rms = librosa.feature.rms(y=y)[0]
        rms_db = librosa.power_to_db(rms**2, ref=np.max)

        peak = np.max(np.abs(y))
        peak_db = librosa.amplitude_to_db(np.array([peak]))[0]

        average_rms = float(np.mean(rms_db))
        peak_amplitude = float(peak_db)
        dynamic_range_db = float(peak_db - np.min(rms_db))

        rms_std = float(np.std(rms_db))
        dynamic_consistency = float(1.0 / (1.0 + rms_std / 10.0))
        dynamic_consistency = max(0.0, min(1.0, dynamic_consistency))

        frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        amplitude_envelope = [
            {
                "time": float(time),
                "rms": float(rms_db_val),
            }
            for time, rms_db_val in zip(frame_times[::10], rms_db[::10], strict=False)
        ]

        return {
            "average_rms": average_rms,
            "peak_amplitude": peak_amplitude,
            "dynamic_range_db": dynamic_range_db,
            "lufs": average_rms,
            "amplitude_envelope": amplitude_envelope,
            "dynamic_consistency": dynamic_consistency,
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
            "message": f"Dynamics analysis failed: {str(e)}",
        }
