"""Key detection module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory


def get_detect_key_tool() -> Tool:
    """Get the detect_key tool definition"""
    return Tool(
        name="detect_key",
        description="Detect the musical key and mode (major/minor) of the audio. Useful for harmonic analysis and understanding the tonal center.",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Detect the musical key and mode (major/minor) of the audio.

Returns: dict with key (e.g., "C major"), confidence (0.0-1.0), mode ("major" or "minor"), tonic (root note), alternative_keys (list of alternative key candidates)

Interpretation Guidelines:
- confidence: >0.8 high confidence, 0.6-0.8 moderate, <0.6 low (may be ambiguous or atonal)
- mode: "major" or "minor" - affects the emotional character and harmonic expectations
- tonic: Root note of the key - use with chord detection to understand harmonic function
- alternative_keys: Other possible keys if confidence is moderate - check these if the primary key seems wrong
- Use with detect_chords to understand harmonic progressions and chord functions
- When confidence is low, the piece may be modal, atonal, or modulate frequently
- Major keys typically sound brighter; minor keys sound darker or more emotional
- Combine with comprehensive_analysis for full harmonic understanding
- Useful for explaining why certain chords work together and suggesting scale practice""",
    )


# Krumhansl-Schmuckler key profiles
KEY_PROFILE_MAJOR = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
KEY_PROFILE_MINOR = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def krumhansl_key_correlations(chroma_mean: np.ndarray) -> tuple[list[float], list[float]]:
    """Correlate a mean chroma vector against Krumhansl-Schmuckler key profiles.

    Returns (correlations_major, correlations_minor), each a list of 12 raw
    Pearson correlations indexed by tonic pitch class (C=0 ... B=11).
    """
    correlations_major = []
    correlations_minor = []

    for i in range(12):
        rotated_chroma = np.roll(chroma_mean, -i)
        corr_major = np.corrcoef(rotated_chroma, KEY_PROFILE_MAJOR)[0, 1]
        corr_minor = np.corrcoef(rotated_chroma, KEY_PROFILE_MINOR)[0, 1]
        correlations_major.append(float(corr_major) if not np.isnan(corr_major) else 0.0)
        correlations_minor.append(float(corr_minor) if not np.isnan(corr_minor) else 0.0)

    return correlations_major, correlations_minor


def estimate_key_from_chroma(chroma_mean: np.ndarray) -> tuple[str, str, str, float]:
    """Estimate the key from a mean chroma vector using Krumhansl profiles.

    Returns (key_name like "C major", mode, tonic, raw correlation).
    """
    correlations_major, correlations_minor = krumhansl_key_correlations(chroma_mean)
    max_major_idx = int(np.argmax(correlations_major))
    max_minor_idx = int(np.argmax(correlations_minor))

    if correlations_major[max_major_idx] > correlations_minor[max_minor_idx]:
        tonic = NOTE_NAMES[max_major_idx]
        return f"{tonic} major", "major", tonic, correlations_major[max_major_idx]
    tonic = NOTE_NAMES[max_minor_idx]
    return f"{tonic} minor", "minor", tonic, correlations_minor[max_minor_idx]


async def detect_key(audio_path: str) -> dict[str, Any]:
    """Detect musical key"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        # CQT chroma: log-spaced bins keep pitch-class resolution in the low
        # register (bass), where linear STFT bins smear adjacent semitones.
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        note_names = NOTE_NAMES

        correlations_major, correlations_minor = krumhansl_key_correlations(chroma_mean)

        max_major_idx = np.argmax(correlations_major)
        max_minor_idx = np.argmax(correlations_minor)
        max_major_corr = correlations_major[max_major_idx]
        max_minor_corr = correlations_minor[max_minor_idx]

        if max_major_corr > max_minor_corr:
            key_name = f"{note_names[max_major_idx]} major"
            mode = "major"
            best_corr = float(max_major_corr)
            tonic = note_names[max_major_idx]
        else:
            key_name = f"{note_names[max_minor_idx]} minor"
            mode = "minor"
            best_corr = float(max_minor_corr)
            tonic = note_names[max_minor_idx]

        all_correlations = [(correlations_major[i], note_names[i], "major") for i in range(12)]
        all_correlations.extend(
            [(correlations_minor[i], note_names[i], "minor") for i in range(12)]
        )
        all_correlations.sort(reverse=True, key=lambda x: x[0])

        # Margin-based confidence: how far the winner stands above the
        # runner-up, scaled by how good the winning correlation is. The old
        # (corr+1)/2 remap reported ~0.75+ even for near-ties.
        runner_up_corr = all_correlations[1][0] if len(all_correlations) > 1 else 0.0
        margin = max(0.0, best_corr - runner_up_corr)
        confidence = max(0.0, min(1.0, best_corr)) * min(1.0, 0.5 + margin * 2.5)
        confidence = float(max(0.0, min(1.0, confidence)))

        alternative_keys = []
        for corr, note, m in all_correlations[1:4]:
            if f"{note} {m}" != key_name:
                alternative_keys.append(
                    {
                        "key": f"{note} {m}",
                        "confidence": float(max(0.0, min(1.0, corr))),
                    }
                )

        return {
            "key": key_name,
            "confidence": confidence,
            "mode": mode,
            "tonic": tonic,
            "alternative_keys": alternative_keys,
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
            "message": f"Key detection failed: {str(e)}",
        }
