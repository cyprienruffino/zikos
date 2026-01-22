"""Dynamics and amplitude analysis module"""

from typing import Any

import librosa
import numpy as np
import soundfile as sf

from zikos.constants import AUDIO
from zikos.mcp.tool import Tool, ToolCategory


def get_analyze_dynamics_tool() -> Tool:
    """Get the analyze_dynamics tool definition"""
    return Tool(
        name="analyze_dynamics",
        description="Analyze amplitude and dynamic range. Returns: dynamic_range (dB), dynamic_consistency (0.0-1.0), average_amplitude, peak_amplitude",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze amplitude and dynamic range.

Returns: dict with dynamic_range (dB), dynamic_consistency (0.0-1.0), average_amplitude, peak_amplitude

Interpretation Guidelines:
- dynamic_range: >20dB excellent, 15-20dB good, 10-15dB needs work, <10dB poor
- dynamic_consistency: >0.85 excellent, 0.75-0.85 good, <0.75 needs work
- If dynamic_consistency < 0.75, suggest focusing on consistent technique""",
    )


async def analyze_dynamics(audio_path: str) -> dict[str, Any]:
    """Analyze amplitude and dynamic range"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < AUDIO.MIN_AUDIO_DURATION:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": f"Audio is too short (minimum {AUDIO.MIN_AUDIO_DURATION} seconds required)",
            }

        rms = librosa.feature.rms(y=y)[0]
        rms_db = librosa.power_to_db(rms**2, ref=np.max)

        peak = np.max(np.abs(y))
        peak_db = librosa.amplitude_to_db(np.array([peak]))[0]

        average_rms = float(np.mean(rms_db))
        peak_amplitude = float(peak_db)
        dynamic_range_db = float(peak_db - np.min(rms_db))

        rms_std = float(np.std(rms_db))
        dynamic_consistency = float(1.0 / (1.0 + rms_std / AUDIO.DYNAMIC_CONSISTENCY_DIVISOR))
        dynamic_consistency = max(0.0, min(1.0, dynamic_consistency))

        frame_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        amplitude_envelope = [
            {
                "time": float(time),
                "rms": float(rms_db_val),
            }
            for time, rms_db_val in zip(
                frame_times[:: AUDIO.AMPLITUDE_ENVELOPE_DOWNSAMPLE],
                rms_db[:: AUDIO.AMPLITUDE_ENVELOPE_DOWNSAMPLE],
                strict=False,
            )
        ]

        peaks = []
        if len(amplitude_envelope) > 0:
            max_rms = max(env["rms"] for env in amplitude_envelope)
            for env in amplitude_envelope:
                if env["rms"] >= max_rms * AUDIO.PEAK_THRESHOLD_RATIO:
                    peaks.append({"time": env["time"], "amplitude": env["rms"]})

        is_consistent = dynamic_consistency > AUDIO.DYNAMIC_CONSISTENCY_THRESHOLD

        return {
            "average_rms": average_rms,
            "average_loudness": average_rms,
            "peak_amplitude": peak_amplitude,
            "dynamic_range_db": dynamic_range_db,
            "dynamic_range": dynamic_range_db,
            "lufs": average_rms,
            "amplitude_envelope": amplitude_envelope,
            "dynamic_consistency": dynamic_consistency,
            "is_consistent": is_consistent,
            "peaks": peaks,
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
