"""Tempo analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.constants import AUDIO
from zikos.mcp.tool import Tool, ToolCategory


def get_analyze_tempo_tool() -> Tool:
    """Get the analyze_tempo tool definition"""
    return Tool(
        name="analyze_tempo",
        description="Analyze tempo/BPM and timing consistency. Returns: bpm, tempo_stability_score (0.0-1.0), tempo_changes, mean_inter_beat_interval_ms",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze tempo/BPM and timing consistency.

Returns: dict with bpm, tempo_stability_score (0.0-1.0), tempo_changes, mean_inter_beat_interval_ms

Interpretation Guidelines:
- tempo_stability_score: >0.90 excellent, 0.80-0.90 good, <0.80 needs work
- mean_inter_beat_interval_ms vs 60000/bpm: shorter = rushing, longer = dragging
- tempo_changes: time-series of local BPM — use to identify where tempo drifts""",
    )


async def analyze_tempo(audio_path: str) -> dict[str, Any]:
    """Analyze tempo/BPM and timing consistency"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < AUDIO.MIN_AUDIO_DURATION:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": f"Audio is too short (minimum {AUDIO.MIN_AUDIO_DURATION} seconds required)",
            }

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, "item"):
            tempo = float(tempo.item())
        elif isinstance(tempo, list | np.ndarray) and len(tempo) > 0:
            tempo = float(tempo[0])
        else:
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

        tempo_changes = []
        if len(beat_times) > 4:
            window_size = min(AUDIO.TEMPO_WINDOW_SIZE, len(beat_times) // 2)
            for i in range(0, len(beat_times) - window_size, window_size):
                window_beats = beat_times[i : i + window_size]
                window_ibis = np.diff(window_beats)
                window_tempo = 60.0 / np.mean(window_ibis)
                tempo_changes.append(
                    {
                        "time": float(beat_times[i]),
                        "bpm": float(window_tempo),
                        "confidence": AUDIO.TEMPO_CONFIDENCE,
                    }
                )

        mean_inter_beat_interval_ms = float(np.mean(inter_beat_intervals) * 1000)

        return {
            "bpm": tempo,
            "confidence": AUDIO.TEMPO_CONFIDENCE,
            "tempo_stability_score": float(tempo_stability),
            "tempo_changes": tempo_changes,
            "mean_inter_beat_interval_ms": mean_inter_beat_interval_ms,
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
