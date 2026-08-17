"""Dynamics and amplitude analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.constants import AUDIO
from zikos.mcp.tool import Tool, ToolCategory


def get_analyze_dynamics_tool() -> Tool:
    """Get the analyze_dynamics tool definition"""
    return Tool(
        name="analyze_dynamics",
        description="Analyze amplitude and dynamic range. Returns: average_rms_db (dBFS), peak_db (dBFS), dynamic_range_db, dynamic_consistency (0.0-1.0), amplitude_envelope, peaks",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze amplitude and dynamic range.

Returns: dict with average_rms_db (dBFS), peak_db (dBFS), dynamic_range_db (spread of the loudness envelope in dB), dynamic_consistency (0.0-1.0), amplitude_envelope (time/rms_db points), peaks (loudest moments, within 3 dB of the maximum)

All dB values share one reference (full scale, dBFS), so they are directly comparable.

Interpretation Guidelines:
- dynamic_range_db: >20dB excellent, 15-20dB good, 10-15dB needs work, <10dB poor
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

        # One shared dB reference: full scale (ref=1.0), i.e. dBFS.
        rms = librosa.feature.rms(y=y)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=1.0)

        peak = float(np.max(np.abs(y)))
        peak_db = float(librosa.amplitude_to_db(np.array([peak]), ref=1.0)[0])

        average_rms_db = float(np.mean(rms_db))

        # Dynamic range: spread of the loudness envelope. Percentiles make it
        # robust to brief silences (which would otherwise pin the minimum at
        # the dB floor).
        dynamic_range_db = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 5))

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

        # Peaks: envelope points within 3 dB of the loudest point. dB values
        # are negative, so the threshold must be additive, not multiplicative.
        peaks = []
        if len(amplitude_envelope) > 0:
            max_rms = max(env["rms"] for env in amplitude_envelope)
            for env in amplitude_envelope:
                if env["rms"] >= max_rms - 3.0:
                    peaks.append({"time": env["time"], "amplitude": env["rms"]})

        return {
            "average_rms_db": average_rms_db,
            "peak_db": peak_db,
            "dynamic_range_db": dynamic_range_db,
            "amplitude_envelope": amplitude_envelope,
            "dynamic_consistency": dynamic_consistency,
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
