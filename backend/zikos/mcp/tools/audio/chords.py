"""Chord detection module"""

from typing import Any

import librosa
import numpy as np


def chroma_to_chord(chroma: np.ndarray) -> tuple[str, float]:
    """Convert chroma vector to chord name"""
    chord_templates = {
        "maj": np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]),
        "min": np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]),
        "dim": np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0]),
        "aug": np.array([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]),
    }

    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    best_chord = "Cmaj"
    best_confidence = 0.0

    for root_idx in range(12):
        for chord_type, template in chord_templates.items():
            rotated_template = np.roll(template, root_idx)
            correlation = np.corrcoef(chroma, rotated_template)[0, 1]
            if not np.isnan(correlation) and correlation > best_confidence:
                best_confidence = correlation
                root_note = note_names[root_idx]
                best_chord = (
                    f"{root_note}{chord_type[:3]}" if chord_type != "maj" else f"{root_note}maj"
                )

    return best_chord, float(max(0.0, min(1.0, (best_confidence + 1.0) / 2.0)))


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

        chroma = librosa.feature.chroma_stft(y=y, sr=sr)

        frame_times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr)

        segments_per_second = 2
        hop_length = int(sr / segments_per_second)

        chords = []
        progression: list[str] = []

        for i in range(0, chroma.shape[1], hop_length):
            segment_chroma = np.mean(chroma[:, i : i + hop_length], axis=1)
            chord_name, confidence = chroma_to_chord(segment_chroma)

            time_start = float(frame_times[i])
            time_end = float(frame_times[min(i + hop_length, len(frame_times) - 1)])

            if confidence > 0.3:
                chords.append(
                    {
                        "time": time_start,
                        "duration": time_end - time_start,
                        "chord": chord_name,
                        "confidence": confidence,
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
