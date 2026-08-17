"""Pitch detection and intonation analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.mcp.tool import Tool, ToolCategory


def get_detect_pitch_tool() -> Tool:
    """Get the detect_pitch tool definition"""
    return Tool(
        name="detect_pitch",
        description="Detect pitch and notes with intonation analysis. Returns: notes (start_time, end_time, duration, pitch, frequency, confidence), intonation_accuracy (0.0-1.0), pitch_stability (0.0-1.0), detected_key, sharp_tendency, flat_tendency, average_cents_deviation",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Detect pitch and notes with intonation analysis.

Returns: dict with notes (with start_time, end_time, duration, pitch, frequency, confidence), intonation_accuracy (0.0-1.0), pitch_stability (0.0-1.0), detected_key, sharp_tendency, flat_tendency, average_cents_deviation

Interpretation Guidelines:
- intonation_accuracy: >0.90 excellent, 0.80-0.90 good, 0.70-0.80 needs work, <0.70 poor
- average_cents_deviation: <5 excellent, 5-15 good, 15-30 needs work, >30 poor
- pitch_stability: >0.90 excellent, 0.80-0.90 good, <0.80 needs work
- Reasoning patterns:
  * intonation_accuracy < 0.70 BUT pitch_stability > 0.85 → likely systematic issue (tuning, finger placement habit)
  * intonation_accuracy < 0.70 AND pitch_stability < 0.75 → likely technique issue (inconsistent pressure, hand position)
  * sharp_tendency > 0.15 → consistently sharp, check finger placement
  * flat_tendency > 0.15 → consistently flat, check finger placement""",
    )


def frequency_to_note(freq: float) -> tuple[str, int]:
    """Convert frequency to note name and octave"""
    if freq <= 0:
        return "C", 0

    A4 = 440.0
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    semitones = 12 * np.log2(freq / A4)
    note_number = int(round(semitones)) + 57
    octave = note_number // 12
    note_index = note_number % 12

    return note_names[note_index], octave


def frequency_to_cents(freq: float, reference_freq: float) -> float:
    """Convert frequency difference to cents"""
    if freq <= 0 or reference_freq <= 0:
        return 0.0
    return float(1200 * np.log2(freq / reference_freq))


def cents_from_nearest_semitone(frequencies: np.ndarray) -> np.ndarray:
    """Signed cents deviation of each frequency from its NEAREST equal-tempered semitone.

    Always in [-50, +50]; octave-invariant, so it works for melodies, not just
    a single sustained note.
    """
    frequencies = np.asarray(frequencies, dtype=float)
    frequencies = frequencies[frequencies > 0]
    if len(frequencies) == 0:
        return np.array([])
    midi = 69.0 + 12.0 * np.log2(frequencies / 440.0)
    return np.asarray((midi - np.round(midi)) * 100.0)


def intonation_score_from_cents(avg_abs_cents: float) -> float:
    """Map mean absolute cents deviation to a 0.0-1.0 accuracy score"""
    if avg_abs_cents < 5:
        return 1.0
    elif avg_abs_cents < 15:
        return 0.9
    elif avg_abs_cents < 30:
        return float(0.8 - (avg_abs_cents - 15) / 150)
    else:
        return float(max(0.0, 0.7 - (avg_abs_cents - 30) / 200))


async def detect_pitch(audio_path: str) -> dict[str, Any]:
    """Detect pitch and notes with intonation analysis"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        hop_length = 512
        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            sr=sr,
            fmin=float(librosa.note_to_hz("C1")),
            fmax=float(librosa.note_to_hz("C7")),
            frame_length=4096,
            hop_length=hop_length,
        )

        valid_f0 = f0[voiced_flag & (voiced_prob > 0.5)]

        if len(valid_f0) == 0:
            return {
                "error": True,
                "error_type": "NO_PITCH_DETECTED",
                "message": "Could not detect pitch in audio",
            }

        onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
        onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=hop_length)

        notes: list[dict[str, Any]] = []
        for i, onset_time in enumerate(onset_times):
            if i < len(onset_times) - 1:
                end_time = onset_times[i + 1]
            else:
                end_time = len(y) / sr

            onset_frame = librosa.time_to_frames(onset_time, sr=sr, hop_length=hop_length)
            end_frame = librosa.time_to_frames(end_time, sr=sr, hop_length=hop_length)

            segment_f0 = f0[onset_frame:end_frame]
            segment_voiced = voiced_flag[onset_frame:end_frame]
            segment_prob = voiced_prob[onset_frame:end_frame]

            valid_segment_f0 = segment_f0[segment_voiced & (segment_prob > 0.5)]

            if len(valid_segment_f0) > 0:
                avg_freq = np.mean(valid_segment_f0)
                note_name, octave = frequency_to_note(avg_freq)
                pitch_name = f"{note_name}{octave}"

                confidence = np.mean(segment_prob[segment_voiced & (segment_prob > 0.5)])

                notes.append(
                    {
                        "start_time": float(onset_time),
                        "end_time": float(end_time),
                        "duration": float(end_time - onset_time),
                        "pitch": pitch_name,
                        "frequency": float(avg_freq),
                        "confidence": float(confidence),
                    }
                )

        # Intonation: per-frame signed cents deviation from the NEAREST
        # equal-tempered semitone (octave-invariant, melody-safe).
        frame_cents = cents_from_nearest_semitone(valid_f0)
        average_cents_deviation = float(np.mean(np.abs(frame_cents)))
        intonation_accuracy = intonation_score_from_cents(average_cents_deviation)

        # Sharp/flat tendency: fraction of frames noticeably above/below
        # the nearest semitone (signed deviations).
        sharp_tendency = float(np.mean(frame_cents > 10.0))
        flat_tendency = float(np.mean(frame_cents < -10.0))

        # Pitch stability: variance of f0 WITHIN each note segment (in cents,
        # relative to the note's median), aggregated across notes. Whole-take
        # variance would penalize melodies for simply containing different notes.
        within_note_stds = []
        for n in notes:
            start_frame = librosa.time_to_frames(
                float(n["start_time"]), sr=sr, hop_length=hop_length
            )
            end_frame = librosa.time_to_frames(float(n["end_time"]), sr=sr, hop_length=hop_length)
            seg = f0[start_frame:end_frame]
            seg = seg[np.isfinite(seg)]
            seg = seg[seg > 0]
            if len(seg) >= 3:
                median_f = float(np.median(seg))
                cents = 1200.0 * np.log2(seg / median_f)
                within_note_stds.append(float(np.std(cents)))

        if within_note_stds:
            mean_within_note_std = float(np.mean(within_note_stds))
        else:
            # No usable note segments: fall back to frame-level deviation spread
            mean_within_note_std = float(np.std(frame_cents)) if len(frame_cents) else 0.0

        pitch_stability = float(max(0.0, min(1.0, 1.0 / (1.0 + mean_within_note_std / 50.0))))

        detected_key = "unknown"
        if len(notes) > 0:
            try:
                from zikos.mcp.tools.audio.key import estimate_key_from_chroma

                chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                chroma_mean = np.mean(chroma, axis=1)
                detected_key, _, _, _ = estimate_key_from_chroma(chroma_mean)
            except Exception:
                detected_key = "unknown"

        return {
            "notes": notes,
            "intonation_accuracy": float(intonation_accuracy),
            "average_cents_deviation": average_cents_deviation,
            "pitch_stability": float(pitch_stability),
            "detected_key": detected_key,
            "sharp_tendency": float(sharp_tendency),
            "flat_tendency": float(flat_tendency),
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
            "message": f"Pitch detection failed: {str(e)}",
        }
