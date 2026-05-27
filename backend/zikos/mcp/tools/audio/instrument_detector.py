"""Instrument metrics — raw signals for the LLM to interpret"""

from typing import Any

import librosa
import numpy as np


async def detect_instrument(audio_path: str) -> dict[str, Any]:
    """Return instrument-discriminating metrics.

    Typical ranges by instrument:
    - Bass (electric/upright): spectral_centroid 300-900 Hz, f0_median 40-300 Hz
    - Guitar: spectral_centroid 500-2000 Hz, f0_median 80-1200 Hz
    - Piano: spectral_centroid 900-3000+ Hz, pitch_confidence > 0.85
    - Voice: spectral_centroid 600-3000 Hz, f0_median 100-1000 Hz

    The LLM should cross-check these values against the user's declared instrument
    and flag any mismatch before giving feedback.
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        mean_centroid = float(np.mean(centroid))

        f0, voiced_flag, voiced_prob = librosa.pyin(
            y,
            fmin=float(librosa.note_to_hz("C1")),
            fmax=float(librosa.note_to_hz("C8")),
            sr=sr,
            frame_length=4096,
        )

        voiced_f0 = f0[voiced_flag] if voiced_flag is not None and f0 is not None else np.array([])
        pitch_confidence = float(np.mean(voiced_flag)) if voiced_flag is not None else 0.0

        harmonics = librosa.effects.harmonic(y)
        harmonic_ratio = float(np.mean(harmonics**2) / (np.mean(y**2) + 1e-10))

        return {
            "spectral_centroid_hz": round(mean_centroid, 1),
            "f0_median_hz": round(float(np.median(voiced_f0)), 1) if len(voiced_f0) > 0 else None,
            "f0_min_hz": round(float(np.min(voiced_f0)), 1) if len(voiced_f0) > 0 else None,
            "f0_max_hz": round(float(np.max(voiced_f0)), 1) if len(voiced_f0) > 0 else None,
            "pitch_confidence": round(pitch_confidence, 3),
            "harmonic_ratio": round(harmonic_ratio, 3),
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
            "message": f"Instrument metrics failed: {str(e)}",
        }
