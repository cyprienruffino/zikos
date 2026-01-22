"""Timbre and spectral analysis module"""

from typing import Any

import librosa
import numpy as np

from zikos.constants import AUDIO
from zikos.mcp.tool import Tool, ToolCategory


def get_analyze_timbre_tool() -> Tool:
    """Get the analyze_timbre tool definition"""
    return Tool(
        name="analyze_timbre",
        description="Analyze timbre and spectral characteristics to assess tone quality and identify instruments. Returns: brightness (0.0-1.0), warmth (0.0-1.0), sharpness, spectral_centroid (Hz), spectral_rolloff, spectral_bandwidth, timbre_consistency, attack_time, harmonic_ratio (0.0-1.0)",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Analyze timbre and spectral characteristics to assess tone quality and identify instruments. Useful for evaluating tone production and technique.

Returns: dict with brightness (0.0-1.0), warmth (0.0-1.0), sharpness, spectral_centroid (Hz), spectral_rolloff, spectral_bandwidth, timbre_consistency, attack_time, harmonic_ratio (0.0-1.0)

Interpretation Guidelines:
- brightness: >0.7 high (violin, flute, trumpet), 0.4-0.7 medium (piano, guitar, saxophone), <0.4 low (cello, bass, trombone)
- warmth: >0.6 high (cello, bass, trombone), 0.4-0.6 medium (piano, guitar, saxophone), <0.4 low (violin, flute, piccolo)
- harmonic_ratio: >0.8 high (piano, strings, wind), 0.5-0.8 medium (guitar, some brass), <0.5 low (drums, percussion)
- spectral_centroid: >3000Hz bright, 1500-3000Hz balanced, <1500Hz warm
- Instrument identification patterns:
  * Piano: High harmonic_ratio (>0.85) + fast attack (<0.01) + medium brightness (0.5-0.7)
  * Guitar: Medium harmonic_ratio (0.6-0.8) + fast attack (<0.02) + medium warmth (0.4-0.6)
  * Violin: High brightness (>0.7) + high harmonic_ratio (>0.8) + fast attack (<0.02)
  * Bass: Low brightness (<0.4) + high warmth (>0.6) + low spectral centroid (<1500Hz)
- Combine brightness, warmth, harmonic_ratio, and attack_time to make identification. Provide confidence levels and explain which characteristics led to your conclusion.""",
    )


async def analyze_timbre(audio_path: str) -> dict[str, Any]:
    """Analyze timbre and spectral characteristics"""
    try:
        y, sr = librosa.load(audio_path, sr=None)

        if len(y) / sr < AUDIO.MIN_AUDIO_DURATION:
            return {
                "error": True,
                "error_type": "TOO_SHORT",
                "message": f"Audio is too short (minimum {AUDIO.MIN_AUDIO_DURATION} seconds required)",
            }

        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]

        mean_centroid = float(np.mean(spectral_centroids))
        mean_rolloff = float(np.mean(spectral_rolloff))
        mean_bandwidth = float(np.mean(spectral_bandwidth))

        brightness = float(min(1.0, mean_centroid / AUDIO.BRIGHTNESS_DIVISOR))

        stft = librosa.stft(y, n_fft=AUDIO.STFT_N_FFT)
        magnitude = np.abs(stft)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=AUDIO.STFT_N_FFT)

        low_freq_mask = freqs < AUDIO.LOW_FREQ_THRESHOLD
        high_freq_mask = freqs >= AUDIO.HIGH_FREQ_THRESHOLD

        low_freq_sum = np.sum(magnitude[low_freq_mask, :])
        high_freq_sum = np.sum(magnitude[high_freq_mask, :])
        low_freq_energy = float(
            low_freq_sum.item() if hasattr(low_freq_sum, "item") else low_freq_sum
        )
        high_freq_energy = float(
            high_freq_sum.item() if hasattr(high_freq_sum, "item") else high_freq_sum
        )
        total_energy = low_freq_energy + high_freq_energy

        if total_energy > 0:
            warmth = float(low_freq_energy / total_energy)
        else:
            warmth = 0.5

        sharpness = float(min(1.0, mean_rolloff / AUDIO.SHARPNESS_DIVISOR))

        centroid_std = float(np.std(spectral_centroids))
        timbre_consistency = float(1.0 / (1.0 + centroid_std / AUDIO.TIMBRE_CONSISTENCY_DIVISOR))
        timbre_consistency = max(0.0, min(1.0, timbre_consistency))

        onsets = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onsets, sr=sr)
        attack_times = []
        for onset_time in onset_times[:10]:
            onset_frame = librosa.time_to_frames(onset_time, sr=sr)
            if onset_frame < len(y):
                start_sample = int(onset_frame)
                end_sample = min(int(onset_frame + sr * 0.1), len(y))
                segment = y[start_sample:end_sample]
                if len(segment) > 0:
                    max_idx = int(np.argmax(np.abs(segment)))
                    attack_time_ms = (max_idx / sr) * 1000
                    attack_times.append(attack_time_ms)

        average_attack_time = float(np.mean(attack_times)) if attack_times else 15.0
        attack_time = average_attack_time / 1000.0

        harmonic_ratio = 0.85
        try:
            harmonic, percussive = librosa.effects.hpss(y)
            harmonic_energy = float(np.sum(harmonic**2))
            total_energy_hpss = float(np.sum(y**2))
            if total_energy_hpss > 0:
                harmonic_ratio = float(harmonic_energy / total_energy_hpss)
        except Exception:
            pass

        return {
            "brightness": brightness,
            "warmth": warmth,
            "sharpness": sharpness,
            "spectral_centroid": mean_centroid,
            "spectral_rolloff": mean_rolloff,
            "spectral_bandwidth": mean_bandwidth,
            "timbre_consistency": timbre_consistency,
            "attack_time": float(attack_time),
            "harmonic_ratio": float(harmonic_ratio),
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
