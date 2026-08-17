"""Groove and microtiming analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_analyze_groove_tool() -> Tool:
    """Get the analyze_groove tool definition"""
    return Tool(
        name="analyze_groove",
        description="Analyze microtiming patterns, swing, and groove feel",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze microtiming patterns, swing, and groove feel.

Returns: dict with swing_ratio, feel_score (0.0-1.0), groove_consistency (0.0-1.0), average_microtiming_deviation_ms, microtiming_std_ms. Fields are null (with a "note") when they could not be measured.

Interpretation Guidelines:
- swing_ratio: long/short ratio of paired eighth notes. 1.0 = straight, ~1.5 = light swing, ~2.0 = triplet swing, <0.8 = reverse swing; null when no eighth-note pairs exist (e.g. only quarter notes)
- feel_score: >0.85 excellent groove, 0.75-0.85 good, <0.75 needs work
- groove_consistency: >0.85 very consistent, 0.75-0.85 good, <0.75 inconsistent
- average_microtiming_deviation_ms: <15ms excellent, 15-30ms good, >30ms needs work
- Use to assess jazz, blues, or any style where groove and feel are important""",
    )


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
        # beat_track may return a 0-d/1-element ndarray for tempo
        if hasattr(tempo, "item"):
            tempo = float(np.asarray(tempo).reshape(-1)[0])
        else:
            tempo = float(tempo)
        beat_times = librosa.frames_to_time(beats, sr=sr)

        if len(beat_times) < 2:
            expected_beat_interval = 60.0 / tempo if tempo > 0 else 0.5
        else:
            inter_beat_intervals = np.diff(beat_times)
            expected_beat_interval = float(np.mean(inter_beat_intervals))

        notes: list[str] = []

        # Microtiming: signed deviation (ms) of each onset from its NEAREST
        # beat. Onsets far from any beat (deliberate off-beats/subdivisions)
        # are excluded rather than assigned to a fabricated beat multiple.
        microtiming_deviations = []
        if len(beat_times) > 0:
            attribution_window = 0.25 * expected_beat_interval
            for onset_time in onset_times:
                nearest_beat = beat_times[np.argmin(np.abs(beat_times - onset_time))]
                deviation = onset_time - nearest_beat
                if abs(deviation) <= attribution_window:
                    microtiming_deviations.append(deviation * 1000.0)

        if len(microtiming_deviations) == 0:
            feel_score = None
            groove_consistency = None
            microtiming_mean = None
            microtiming_std = None
            notes.append(
                "No onsets could be attributed to the beat grid, "
                "so microtiming metrics could not be measured."
            )
        else:
            microtiming_std = float(np.std(microtiming_deviations))
            microtiming_mean = float(np.mean(np.abs(microtiming_deviations)))

            groove_consistency = float(max(0.0, min(1.0, 1.0 / (1.0 + microtiming_std / 20.0))))
            feel_score = float(max(0.0, min(1.0, 1.0 / (1.0 + microtiming_mean / 15.0))))

        # Swing ratio from paired eighth-note IOIs anchored to the beat grid:
        # for each beat containing exactly a downbeat onset plus one
        # subdividing onset, ratio = long (downbeat->subdivision) / short
        # (subdivision->next beat). Straight = 1.0, triplet swing = 2.0.
        swing_pairs = []
        if len(beat_times) >= 2:
            attribution_window = 0.25 * expected_beat_interval
            for k in range(len(beat_times) - 1):
                beat_start, beat_end = beat_times[k], beat_times[k + 1]
                in_beat = [
                    t
                    for t in onset_times
                    if beat_start - attribution_window <= t < beat_end - attribution_window
                ]
                if len(in_beat) != 2:
                    continue
                if abs(in_beat[0] - beat_start) > attribution_window:
                    continue
                long_ioi = in_beat[1] - in_beat[0]
                short_ioi = beat_end - in_beat[1]
                if long_ioi <= 0 or short_ioi <= 0:
                    continue
                ratio = float(long_ioi / short_ioi)
                if 0.25 <= ratio <= 4.0:
                    swing_pairs.append(ratio)

        if swing_pairs:
            swing_ratio = float(np.median(swing_pairs))
        else:
            swing_ratio = None
            notes.append(
                "No eighth-note pairs subdividing the beat were found, "
                "so swing ratio could not be measured."
            )

        result: dict[str, Any] = {
            "swing_ratio": swing_ratio,
            "feel_score": feel_score,
            "groove_consistency": groove_consistency,
            "average_microtiming_deviation_ms": microtiming_mean,
            "microtiming_std_ms": microtiming_std,
        }
        if notes:
            result["note"] = " ".join(notes)
        return result
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
