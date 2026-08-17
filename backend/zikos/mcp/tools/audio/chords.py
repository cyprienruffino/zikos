"""Chord detection module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory


def get_detect_chords_tool() -> Tool:
    """Get the detect_chords tool definition"""
    return Tool(
        name="detect_chords",
        description="Detect chord progression with chord names and timing. Identifies which chords are played and when they occur in the audio.",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Detect chord progression with chord names and timing.

Returns: dict with chords (list of chord objects with time, duration, chord name, confidence) and progression (simplified list of unique chord names in order)

Interpretation Guidelines:
- confidence: >0.7 high confidence, 0.5-0.7 moderate, <0.5 low (may be ambiguous or complex chord)
- progression: Shows the chord sequence without timing, useful for identifying song structure
- chords: Full timing information for each chord change
- Common progressions: I-V-vi-IV (C-G-Am-F), vi-IV-I-V (Am-F-C-G), I-vi-IV-V (C-Am-F-G)
- When confidence is consistently low, the audio may contain complex chords (7ths, 9ths, sus chords) or multiple instruments playing different harmonies
- Use with detect_key to understand the harmonic context and suggest chord substitutions or extensions""",
    )


# Suffixes follow standard chord symbols: "" = major, "m" = minor,
# "dim" = diminished, "aug" = augmented.
CHORD_TEMPLATES = {
    "": np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]),
    "m": np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]),
    "dim": np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0]),
    "aug": np.array([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]),
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def chroma_to_chord(chroma: np.ndarray) -> tuple[str, float]:
    """Convert chroma vector to (chord name, raw template correlation).

    The returned correlation is the raw Pearson correlation in [-1, 1];
    callers should gate on it directly (values near or below 0 mean no
    meaningful match).
    """
    best_chord = "C"
    best_correlation = -1.0

    for root_idx in range(12):
        for suffix, template in CHORD_TEMPLATES.items():
            rotated_template = np.roll(template, root_idx)
            correlation = np.corrcoef(chroma, rotated_template)[0, 1]
            if not np.isnan(correlation) and correlation > best_correlation:
                best_correlation = correlation
                best_chord = f"{NOTE_NAMES[root_idx]}{suffix}"

    return best_chord, float(best_correlation)


async def detect_chords(audio_path: str) -> dict[str, Any]:
    """Detect chord progression"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        hop_length = 512
        # CQT chroma: log-spaced bins keep pitch-class resolution in the low
        # register (bass), where linear STFT bins smear adjacent semitones.
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        # Segment the chroma sequence in FRAMES (each frame spans hop_length
        # samples), aiming for segments_per_second segments per second.
        segments_per_second = 2
        frames_per_segment = max(1, int((sr / segments_per_second) / hop_length))

        # Frames whose RMS is far below the peak are treated as silence.
        peak_rms = float(np.max(rms)) if len(rms) > 0 else 0.0
        silence_rms = max(1e-4, 0.02 * peak_rms)

        chords = []
        progression: list[str] = []

        for i in range(0, chroma.shape[1], frames_per_segment):
            end_idx = min(i + frames_per_segment, chroma.shape[1])
            segment_chroma = np.mean(chroma[:, i:end_idx], axis=1)

            time_start = float(librosa.frames_to_time(i, sr=sr, hop_length=hop_length))
            time_end = float(librosa.frames_to_time(end_idx, sr=sr, hop_length=hop_length))

            segment_rms = float(np.mean(rms[i : min(end_idx, len(rms))])) if len(rms) > i else 0.0
            if segment_rms < silence_rms:
                chords.append(
                    {
                        "time": time_start,
                        "duration": time_end - time_start,
                        "chord": "N.C.",
                        "confidence": None,
                    }
                )
                continue

            chord_name, correlation = chroma_to_chord(segment_chroma)

            # Gate on the raw template correlation (not a remapped value).
            if correlation > 0.3:
                chords.append(
                    {
                        "time": time_start,
                        "duration": time_end - time_start,
                        "chord": chord_name,
                        "confidence": float(max(0.0, min(1.0, correlation))),
                    }
                )

                if not progression or progression[-1] != chord_name:
                    progression.append(chord_name)

        return {
            "chords": chords,
            "progression": progression,
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
            "message": f"Chord detection failed: {str(e)}",
        }
