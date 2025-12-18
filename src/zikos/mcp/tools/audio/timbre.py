"""Timbre and spectral analysis module"""

from typing import Any

import librosa
import numpy as np


async def analyze_timbre(audio_path: str) -> dict[str, Any]:
    """Analyze timbre and spectral characteristics"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < 0.5:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": "Audio is too short (minimum 0.5 seconds required)",
            }

        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]

        mean_centroid = float(np.mean(spectral_centroids))
        mean_rolloff = float(np.mean(spectral_rolloff))
        mean_bandwidth = float(np.mean(spectral_bandwidth))

        brightness = float(min(1.0, mean_centroid / 5000.0))

        stft = librosa.stft(y, n_fft=2048)
        magnitude = np.abs(stft)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

        low_freq_mask = freqs < 2000
        high_freq_mask = freqs >= 2000

        low_freq_energy = float(np.sum(magnitude[low_freq_mask, :]))
        high_freq_energy = float(np.sum(magnitude[high_freq_mask, :]))
        total_energy = low_freq_energy + high_freq_energy

        if total_energy > 0:
            warmth = float(low_freq_energy / total_energy)
        else:
            warmth = 0.5

        sharpness = float(min(1.0, mean_rolloff / 8000.0))

        centroid_std = float(np.std(spectral_centroids))
        timbre_consistency = float(1.0 / (1.0 + centroid_std / 500.0))
        timbre_consistency = max(0.0, min(1.0, timbre_consistency))

        return {
            "brightness": brightness,
            "warmth": warmth,
            "sharpness": sharpness,
            "spectral_centroid": mean_centroid,
            "spectral_rolloff": mean_rolloff,
            "spectral_bandwidth": mean_bandwidth,
            "timbre_consistency": timbre_consistency,
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
            "message": f"Timbre analysis failed: {str(e)}",
        }
