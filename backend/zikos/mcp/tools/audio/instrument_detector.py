"""Instrument detection from audio characteristics"""

from typing import Any

import librosa
import numpy as np

# Keywords (lowercase) that map each detected class to user profile instrument names.
_INSTRUMENT_KEYWORDS: dict[str, list[str]] = {
    "bass": ["bass", "basse", "contrebasse", "upright", "bajo"],
    "guitar": ["guitar", "guitare", "guitarra"],
    "piano": ["piano", "keyboard", "keys", "clavier", "organ", "orgue", "synth"],
    "voice": ["voice", "voix", "vocal", "chant", "sing"],
}


def _classify(centroid_hz: float, median_f0: float | None) -> tuple[str, float]:
    """Return (instrument_class, confidence) from spectral centroid and median F0."""
    # Bass: low centroid is the primary signal; low F0 reinforces it.
    if centroid_hz < 900:
        if median_f0 is None or median_f0 < 350:
            return "bass", 0.8 if centroid_hz < 650 else 0.65
        # High centroid but low F0 is ambiguous — could be heavily distorted guitar.

    # Piano: bright spectrum with wide, confident pitch range.
    if centroid_hz > 1100:
        return "piano", 0.75 if centroid_hz > 1500 else 0.6

    # Guitar: middle ground.
    if centroid_hz > 500:
        return "guitar", 0.5

    return "unknown", 0.3


async def detect_instrument(audio_path: str) -> dict[str, Any]:
    """Detect the most likely instrument from audio characteristics.

    Returns: detected_class, confidence, spectral_centroid_hz, median_f0_hz
    """
    try:
        y, sr = librosa.load(audio_path, sr=None)

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        mean_centroid = float(np.mean(centroid))

        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=float(librosa.note_to_hz("C1")),
            fmax=float(librosa.note_to_hz("C8")),
            sr=sr,
            frame_length=4096,
        )
        voiced_f0 = f0[voiced_flag] if voiced_flag is not None and f0 is not None else np.array([])
        median_f0: float | None = float(np.median(voiced_f0)) if len(voiced_f0) > 0 else None

        detected_class, confidence = _classify(mean_centroid, median_f0)

        return {
            "detected_class": detected_class,
            "confidence": round(confidence, 2),
            "spectral_centroid_hz": round(mean_centroid, 1),
            "median_f0_hz": round(median_f0, 1) if median_f0 is not None else None,
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
            "message": f"Instrument detection failed: {str(e)}",
        }


def check_instrument_mismatch(detected_class: str, user_instruments: list[str]) -> str | None:
    """Return a warning string if the detected instrument doesn't match the user's declared ones."""
    if not user_instruments or detected_class == "unknown":
        return None
    keywords = _INSTRUMENT_KEYWORDS.get(detected_class, [detected_class])
    match = any(kw in user_inst.lower() for user_inst in user_instruments for kw in keywords)
    if not match:
        declared = ", ".join(user_instruments)
        return (
            f"Detected instrument appears to be {detected_class}, "
            f"but user declared: {declared}. Verify before giving feedback."
        )
    return None
