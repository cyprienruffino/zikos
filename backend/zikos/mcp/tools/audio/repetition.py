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


async def detect_repetitions(audio_path: str) -> dict[str, Any]:
    """Detect repeated patterns in audio"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 2.0:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short for repetition detection (minimum 2 seconds required)",
            }

        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_normalized = librosa.util.normalize(chroma, norm=2, axis=0)

        similarity_matrix = np.dot(chroma_normalized.T, chroma_normalized)

        frame_times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr)

        repetitions = []
        min_pattern_duration = 1.0
        min_similarity = 0.75

        for i in range(len(frame_times) - int(min_pattern_duration * sr / 512)):
            for pattern_length in range(
                int(min_pattern_duration * sr / 512), min(len(frame_times) - i, int(8 * sr / 512))
            ):
                pattern_end = min(i + pattern_length, len(frame_times) - 1)
                pattern_start_time = frame_times[i]
                pattern_end_time = frame_times[pattern_end]

                if pattern_end_time - pattern_start_time < min_pattern_duration:
                    continue

                pattern_similarity = similarity_matrix[
                    i : i + pattern_length, i : i + pattern_length
                ]
                pattern_self_similarity = float(np.mean(np.diag(pattern_similarity)))

                if pattern_self_similarity < 0.6:
                    continue

                repetition_times = []
                for j in range(i + pattern_length, len(frame_times) - pattern_length):
                    comparison_similarity = similarity_matrix[
                        i : i + pattern_length, j : j + pattern_length
                    ]
                    avg_similarity = float(np.mean(comparison_similarity))

                    if avg_similarity >= min_similarity:
                        repetition_start_time = frame_times[j]
                        if repetition_start_time not in repetition_times:
                            repetition_times.append(repetition_start_time)

                if len(repetition_times) > 0:
                    repetitions.append(
                        {
                            "pattern_start": float(pattern_start_time),
                            "pattern_end": float(pattern_end_time),
                            "repetition_times": repetition_times,
                            "similarity": float(pattern_self_similarity),
                        }
                    )

        if len(repetitions) == 0:
            return {
                "repetitions": [],
                "form": "no_repetition",
            }

        repetitions.sort(key=lambda x: float(x["pattern_start"]))  # type: ignore[arg-type]

        form_parts = []
        pattern_labels = {}
        label_counter = 0

        for rep in repetitions:
            pattern_key = (rep["pattern_start"], rep["pattern_end"])
            if pattern_key not in pattern_labels:
                if label_counter < 26:
                    label = chr(ord("A") + label_counter)
                else:
                    label = f"A{chr(ord('A') + (label_counter - 26))}"
                pattern_labels[pattern_key] = label
                label_counter += 1

            label = pattern_labels[pattern_key]
            form_parts.append(label)

        form = "-".join(form_parts) if form_parts else "no_repetition"

        return {
            "repetitions": repetitions[:10],
            "form": form,
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
            "message": f"Failed to detect repetitions: {str(e)}",
        }
