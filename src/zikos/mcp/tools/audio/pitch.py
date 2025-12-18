"""Pitch detection and intonation analysis module"""

from typing import Any

import librosa
import numpy as np


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


def calculate_intonation_accuracy(frequencies: np.ndarray, reference_freq: float) -> float:
    """Calculate intonation accuracy score (0.0-1.0)"""
    if len(frequencies) == 0 or reference_freq <= 0:
        return 0.0

    cents_deviations = [abs(frequency_to_cents(f, reference_freq)) for f in frequencies if f > 0]

    if len(cents_deviations) == 0:
        return 0.0

    avg_cents = float(np.mean(cents_deviations))

    if avg_cents < 5:
        return 1.0
    elif avg_cents < 15:
        return 0.9
    elif avg_cents < 30:
        return float(0.8 - (avg_cents - 15) / 150)
    else:
        return float(max(0.0, 0.7 - (avg_cents - 30) / 200))


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

        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=float(librosa.note_to_hz("C2")),
            fmax=float(librosa.note_to_hz("C7")),
        )

        valid_f0 = f0[voiced_flag & (voiced_prob > 0.5)]

        if len(valid_f0) == 0:
            return {
                "error": True,
                "error_type": "NO_PITCH_DETECTED",
                "message": "Could not detect pitch in audio",
            }

        onsets = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onsets, sr=sr)

        notes = []
        for i, onset_time in enumerate(onset_times):
            if i < len(onset_times) - 1:
                end_time = onset_times[i + 1]
            else:
                end_time = len(y) / sr

            onset_frame = librosa.time_to_frames(onset_time, sr=sr)
            end_frame = librosa.time_to_frames(end_time, sr=sr)

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

        all_frequencies = valid_f0
        if len(all_frequencies) > 0:
            mean_freq = float(np.mean(all_frequencies))
            reference_freq = float(librosa.note_to_hz(frequency_to_note(mean_freq)[0] + str(4)))

            intonation_accuracy = calculate_intonation_accuracy(all_frequencies, reference_freq)

            pitch_variance = np.var(all_frequencies)
            pitch_stability = 1.0 / (1.0 + pitch_variance / (mean_freq**2))
            pitch_stability = max(0.0, min(1.0, pitch_stability))

            sharp_tendency = 0.0
            flat_tendency = 0.0
            if len(notes) > 0:
                sharp_count = 0
                flat_count = 0
                for n in notes:
                    freq = n.get("frequency")
                    if isinstance(freq, int | float):
                        cents = frequency_to_cents(float(freq), reference_freq)
                        if cents > 10:
                            sharp_count += 1
                        elif cents < -10:
                            flat_count += 1
                sharp_tendency = float(sharp_count / len(notes))
                flat_tendency = float(flat_count / len(notes))
        else:
            intonation_accuracy = 0.0
            pitch_stability = 0.0
            sharp_tendency = 0.0
            flat_tendency = 0.0

        detected_key = "unknown"
        if len(notes) > 0 and mean_freq > 0:
            try:
                chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                chroma_mean = np.mean(chroma, axis=1)
                key_idx = np.argmax(chroma_mean)
                note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
                detected_key = f"{note_names[key_idx]} major"
            except Exception:
                detected_key = "unknown"

        return {
            "notes": notes,
            "intonation_accuracy": float(intonation_accuracy),
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
