"""Repetition detection module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_detect_repetitions_tool() -> Tool:
    """Get the detect_repetitions tool definition"""
    return Tool(
        name="detect_repetitions",
        description="Detect repeated patterns and musical form",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Detect repeated patterns and musical form.

Returns: dict with repetitions (list of pattern objects with pattern_start, pattern_end, repetition_times, similarity) and form (string like "A-B-A" or "no_repetition")

Interpretation Guidelines:
- form: Shows musical structure (A-B-A, A-A-B-A, etc.) or "no_repetition" if no clear patterns
- similarity: >0.75 high similarity (likely same section), 0.5-0.75 moderate, <0.5 different sections
- repetitions: Lists detected patterns and when they repeat
- Use to identify song structure, verse/chorus patterns, or repeated motifs
- When form shows clear structure (A-B-A), use this to help students understand the piece's organization
- If no_repetition, the piece may be through-composed or patterns are too subtle to detect
- Minimum 2 seconds of audio required for meaningful repetition detection
- Useful for analyzing longer pieces and helping students understand musical form""",
    )


# Cap analysis length so long files don't blow up segmentation cost.
MAX_ANALYSIS_SECONDS = 180.0

# Target segment length (seconds) for structural segmentation.
TARGET_SEGMENT_SECONDS = 4.0

# Cosine similarity threshold for two segments to count as the same section.
SEGMENT_MATCH_THRESHOLD = 0.85

_HOP_LENGTH = 512


def _segment_label(index: int) -> str:
    """0 -> A, 1 -> B, ..., 26 -> AA, ..."""
    if index < 26:
        return chr(ord("A") + index)
    return chr(ord("A") + index // 26 - 1) + chr(ord("A") + index % 26)


async def detect_repetitions(audio_path: str) -> dict[str, Any]:
    """Detect repeated patterns in audio.

    Segments the piece with librosa's agglomerative structural segmentation
    on chroma features, then clusters segments by cosine similarity of their
    mean chroma so repeated sections share a form label (A-B-A etc.).
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)

        duration = len(y) / sr
        if duration < 2.0:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short for repetition detection (minimum 2 seconds required)",
            }

        truncated = False
        if duration > MAX_ANALYSIS_SECONDS:
            y = y[: int(MAX_ANALYSIS_SECONDS * sr)]
            duration = MAX_ANALYSIS_SECONDS
            truncated = True

        chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=_HOP_LENGTH)
        n_frames = chroma.shape[1]

        # Number of structural segments: about one per TARGET_SEGMENT_SECONDS,
        # clamped to a sane range and to the number of available frames.
        n_segments = int(np.clip(round(duration / TARGET_SEGMENT_SECONDS), 2, 16))
        n_segments = min(n_segments, n_frames)

        boundaries = librosa.segment.agglomerative(chroma, n_segments)
        boundary_times = librosa.frames_to_time(boundaries, sr=sr, hop_length=_HOP_LENGTH)

        # Build segments as (start_time, end_time, mean_chroma)
        segments = []
        boundary_list = list(boundaries) + [n_frames]
        time_list = list(boundary_times) + [duration]
        for idx in range(len(boundary_list) - 1):
            start_f, end_f = int(boundary_list[idx]), int(boundary_list[idx + 1])
            if end_f <= start_f:
                continue
            mean_chroma = np.mean(chroma[:, start_f:end_f], axis=1)
            norm = float(np.linalg.norm(mean_chroma))
            if norm > 0:
                mean_chroma = mean_chroma / norm
            segments.append(
                {
                    "start": float(time_list[idx]),
                    "end": float(time_list[idx + 1]),
                    "chroma": mean_chroma,
                }
            )

        # Greedy clustering: assign each segment to the first earlier label
        # whose representative chroma is similar enough, else a new label.
        labels: list[str] = []
        label_representatives: list[np.ndarray] = []
        label_similarities: list[list[float]] = []
        for seg in segments:
            assigned = None
            for label_idx, rep_chroma in enumerate(label_representatives):
                similarity = float(np.dot(seg["chroma"], rep_chroma))
                if similarity >= SEGMENT_MATCH_THRESHOLD:
                    assigned = label_idx
                    label_similarities[label_idx].append(similarity)
                    break
            if assigned is None:
                assigned = len(label_representatives)
                label_representatives.append(seg["chroma"])
                label_similarities.append([])
            labels.append(_segment_label(assigned))

        # Repetitions: every label that occurs more than once. The first
        # occurrence is the pattern; later occurrences are its repetitions.
        repetitions = []
        for label_idx in range(len(label_representatives)):
            label = _segment_label(label_idx)
            occurrence_indices = [i for i, lb in enumerate(labels) if lb == label]
            if len(occurrence_indices) < 2:
                continue
            first = segments[occurrence_indices[0]]
            sims = label_similarities[label_idx]
            repetitions.append(
                {
                    "pattern_start": first["start"],
                    "pattern_end": first["end"],
                    "repetition_times": [segments[i]["start"] for i in occurrence_indices[1:]],
                    "similarity": float(np.mean(sims)) if sims else 1.0,
                    "label": label,
                }
            )

        if len(repetitions) == 0:
            result: dict[str, Any] = {
                "repetitions": [],
                "form": "no_repetition",
            }
        else:
            result = {
                "repetitions": repetitions[:10],
                "form": "-".join(labels),
            }

        if truncated:
            result["note"] = (
                f"Audio longer than {MAX_ANALYSIS_SECONDS:.0f}s; only the first "
                f"{MAX_ANALYSIS_SECONDS:.0f} seconds were analyzed."
            )

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
            "message": f"Failed to detect repetitions: {str(e)}",
        }
