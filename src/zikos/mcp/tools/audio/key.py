"""Key detection module"""

from typing import Any

import librosa
import numpy as np


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

        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        key_profiles_major = np.array(
            [
                [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
            ]
        )
        key_profiles_minor = np.array(
            [
                [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
            ]
        )

        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        correlations_major = []
        correlations_minor = []

        for i in range(12):
            rotated_chroma = np.roll(chroma_mean, -i)
            corr_major = np.corrcoef(rotated_chroma, key_profiles_major[0])[0, 1]
            corr_minor = np.corrcoef(rotated_chroma, key_profiles_minor[0])[0, 1]
            correlations_major.append(corr_major if not np.isnan(corr_major) else 0.0)
            correlations_minor.append(corr_minor if not np.isnan(corr_minor) else 0.0)

        max_major_idx = np.argmax(correlations_major)
        max_minor_idx = np.argmax(correlations_minor)
        max_major_corr = correlations_major[max_major_idx]
        max_minor_corr = correlations_minor[max_minor_idx]

        if max_major_corr > max_minor_corr:
            key_name = f"{note_names[max_major_idx]} major"
            mode = "major"
            confidence = float(max_major_corr)
            tonic = note_names[max_major_idx]
        else:
            key_name = f"{note_names[max_minor_idx]} minor"
            mode = "minor"
            confidence = float(max_minor_corr)
            tonic = note_names[max_minor_idx]

        confidence = max(0.0, min(1.0, (confidence + 1.0) / 2.0))

        alternative_keys = []
        all_correlations = [(correlations_major[i], note_names[i], "major") for i in range(12)]
        all_correlations.extend(
            [(correlations_minor[i], note_names[i], "minor") for i in range(12)]
        )
        all_correlations.sort(reverse=True, key=lambda x: x[0])

        for corr, note, m in all_correlations[1:4]:
            if f"{note} {m}" != key_name:
                alt_confidence = max(0.0, min(1.0, (corr + 1.0) / 2.0))
                alternative_keys.append(
                    {
                        "key": f"{note} {m}",
                        "confidence": float(alt_confidence),
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
