"""Audio synthesis helpers for realistic test audio generation

Uses librosa and numpy to create instrument-like sounds, not just sine waves.
"""

import math
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


def generate_piano_tone(
    frequency: float, duration: float, sample_rate: int = 44100, velocity: float = 0.7
) -> np.ndarray:
    """Generate a piano-like tone using additive synthesis

    Creates a more realistic piano sound with harmonics and envelope.
    """
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Piano has multiple harmonics with different amplitudes
    # Fundamental + harmonics with decreasing amplitude
    harmonics = [
        (1.0, 1.0),  # Fundamental
        (2.0, 0.5),  # Octave
        (3.0, 0.25),  # Fifth
        (4.0, 0.125),  # Double octave
        (5.0, 0.0625),  # Third
    ]

    signal = np.zeros_like(t)
    for harmonic_freq, amplitude in harmonics:
        signal += amplitude * np.sin(2 * np.pi * frequency * harmonic_freq * t)

    # Apply ADSR envelope (Attack, Decay, Sustain, Release)
    attack_time = 0.01
    decay_time = 0.1
    sustain_level = 0.7
    release_time = 0.2

    envelope = np.ones_like(t)

    # Attack
    attack_samples = int(attack_time * sample_rate)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # Decay
    decay_samples = int(decay_time * sample_rate)
    if decay_samples > 0 and attack_samples + decay_samples < len(envelope):
        decay_start = attack_samples
        decay_end = attack_samples + decay_samples
        envelope[decay_start:decay_end] = np.linspace(1, sustain_level, decay_samples)

    # Sustain (already set)

    # Release
    release_samples = int(release_time * sample_rate)
    if release_samples > 0:
        release_start = len(envelope) - release_samples
        envelope[release_start:] = np.linspace(sustain_level, 0, release_samples)

    signal *= envelope * velocity

    # Normalize
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal)) * 0.8

    return signal


def generate_guitar_tone(frequency: float, duration: float, sample_rate: int = 44100) -> np.ndarray:
    """Generate a guitar-like tone"""
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Guitar has different harmonic content than piano
    harmonics = [
        (1.0, 1.0),
        (2.0, 0.6),
        (3.0, 0.4),
        (4.0, 0.2),
    ]

    signal = np.zeros_like(t)
    for harmonic_freq, amplitude in harmonics:
        signal += amplitude * np.sin(2 * np.pi * frequency * harmonic_freq * t)

    # Guitar has a pluck envelope (fast attack, slower decay)
    envelope = np.exp(-t * 2)  # Exponential decay
    signal *= envelope

    # Add slight vibrato
    vibrato = 1 + 0.02 * np.sin(2 * np.pi * 5 * t)
    signal *= vibrato

    # Normalize
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal)) * 0.8

    return signal


def generate_scale_audio(
    notes: list[str],
    note_duration: float = 0.5,
    instrument: str = "piano",
    sample_rate: int = 44100,
) -> np.ndarray:
    """Generate audio for a scale of notes

    Args:
        notes: List of note names (e.g., ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'])
        note_duration: Duration of each note in seconds
        instrument: 'piano' or 'guitar'
        sample_rate: Sample rate for audio

    Returns:
        Combined audio signal
    """
    audio_segments = []

    for note in notes:
        # Convert note name to frequency
        freq = librosa.note_to_hz(note)

        if instrument == "piano":
            note_audio = generate_piano_tone(freq, note_duration, sample_rate)
        elif instrument == "guitar":
            note_audio = generate_guitar_tone(freq, note_duration, sample_rate)
        else:
            # Fallback to simple sine wave
            t = np.linspace(0, note_duration, int(sample_rate * note_duration))
            note_audio = 0.7 * np.sin(2 * np.pi * freq * t)

        audio_segments.append(note_audio)

    # Add small gaps between notes
    gap_samples = int(0.05 * sample_rate)
    gap = np.zeros(gap_samples)

    result = []
    for i, segment in enumerate(audio_segments):
        result.append(segment)
        if i < len(audio_segments) - 1:
            result.append(gap)

    return np.concatenate(result)


def generate_rhythmic_pattern(
    tempo: float, duration: float, sample_rate: int = 44100
) -> np.ndarray:
    """Generate a rhythmic pattern at a specific tempo

    Creates a simple metronome-like pattern with beats.
    """
    beat_interval = 60.0 / tempo  # Time between beats in seconds
    beats_per_measure = 4

    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.zeros_like(t)

    # Generate beats
    beat_time = 0.0
    beat_number = 0
    while beat_time < duration:
        # Strong beat (first beat of measure) vs weak beat
        if beat_number % beats_per_measure == 0:
            # Strong beat: higher frequency
            beat_freq = 880  # A5
            amplitude = 0.5
        else:
            # Weak beat: lower frequency
            beat_freq = 440  # A4
            amplitude = 0.3

        # Create a short click/tick sound
        beat_duration = 0.05
        beat_samples = int(beat_duration * sample_rate)
        beat_start = int(beat_time * sample_rate)
        beat_end = min(beat_start + beat_samples, len(signal))

        if beat_end > beat_start:
            beat_t = np.linspace(0, beat_duration, beat_end - beat_start)
            beat_signal = amplitude * np.sin(2 * np.pi * beat_freq * beat_t)
            # Apply envelope for click sound
            envelope = np.exp(-beat_t * 30)
            beat_signal *= envelope
            signal[beat_start:beat_end] += beat_signal

        beat_time += beat_interval
        beat_number += 1

    # Normalize
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal)) * 0.8

    return signal


def save_audio_file(audio: np.ndarray, file_path: Path, sample_rate: int = 44100):
    """Save audio array to WAV file"""
    sf.write(str(file_path), audio, sample_rate)


def create_test_audio_file(
    output_path: Path,
    audio_type: str = "scale",
    duration: float = 2.0,
    frequency: float = 440.0,
    tempo: float = 120.0,
    sample_rate: int = 44100,
) -> Path:
    """Create a test audio file with synthesized sound

    Args:
        output_path: Path where to save the audio file
        audio_type: Type of audio to generate:
            - 'scale': A musical scale (C major)
            - 'single_note': Single note at given frequency
            - 'rhythm': Rhythmic pattern at given tempo
        duration: Duration in seconds (for single_note and rhythm)
        frequency: Frequency in Hz (for single_note)
        tempo: BPM (for rhythm)
        sample_rate: Audio sample rate

    Returns:
        Path to created audio file
    """
    if audio_type == "scale":
        # C major scale
        notes = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
        audio = generate_scale_audio(notes, note_duration=duration / len(notes))
    elif audio_type == "single_note":
        audio = generate_piano_tone(frequency, duration, sample_rate)
    elif audio_type == "rhythm":
        audio = generate_rhythmic_pattern(tempo, duration, sample_rate)
    else:
        raise ValueError(f"Unknown audio_type: {audio_type}")

    save_audio_file(audio, output_path, sample_rate)
    return output_path
