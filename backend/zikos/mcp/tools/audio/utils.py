"""Utility functions for audio analysis"""

import re
from pathlib import Path
from typing import Any

from zikos.config import settings
from zikos.constants import (
    DEFAULT_INSTRUMENT_DSP_PROFILE,
    INSTRUMENT_DSP_PROFILES,
    InstrumentDSPProfile,
)

# Substring → canonical profile name. Checked in order: "bass" first so
# "bass guitar" resolves to bass, not guitar.
_INSTRUMENT_ALIASES: tuple[tuple[str, str], ...] = (
    ("bass", "bass"),
    ("guitar", "guitar"),
    ("ukulele", "guitar"),
    ("piano", "piano"),
    ("keyboard", "piano"),
    ("keys", "piano"),
    ("synth", "piano"),
    ("voice", "voice"),
    ("vocal", "voice"),
    ("sing", "voice"),
    ("violin", "violin"),
    ("fiddle", "violin"),
)


def resolve_instrument_profile(instrument: Any) -> tuple[str, InstrumentDSPProfile]:
    """Map a free-form instrument name to (canonical name, DSP profile).

    Accepts anything the LLM or user settings might supply ("bass guitar",
    "Electric Bass", "keys"); unknown or missing names fall back to the wide
    default profile under the name "default".
    """
    if not isinstance(instrument, str) or not instrument.strip():
        return "default", DEFAULT_INSTRUMENT_DSP_PROFILE
    name = instrument.strip().lower()
    if name in INSTRUMENT_DSP_PROFILES:
        return name, INSTRUMENT_DSP_PROFILES[name]
    for alias, canonical in _INSTRUMENT_ALIASES:
        if alias in name:
            return canonical, INSTRUMENT_DSP_PROFILES[canonical]
    return "default", DEFAULT_INSTRUMENT_DSP_PROFILE


UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def is_valid_audio_file_id(audio_file_id: Any) -> bool:
    """Check that an audio_file_id looks like the UUIDs this system issues"""
    return isinstance(audio_file_id, str) and bool(UUID_REGEX.match(audio_file_id))


def resolve_audio_path(audio_file_id: str) -> Path:
    """Resolve audio_file_id to file path"""
    storage_path = Path(settings.audio_storage_path)
    file_path = storage_path / f"{audio_file_id}.wav"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Audio file '{audio_file_id}' not found. "
            "audio_file_id must be a UUID returned by a prior tool call in the current session "
            "(e.g. from the audio upload notification, midi_to_audio, time_stretch, or pitch_shift). "
            "Do not fabricate or guess IDs."
        )

    return file_path


def create_error_response(
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create structured error response"""
    response = {
        "error": True,
        "error_type": error_type,
        "message": message,
    }
    if details:
        response["details"] = details
    return response


def validate_audio_duration(
    audio: Any, sample_rate: int, min_duration: float = 0.5
) -> tuple[bool, str | None]:
    """Validate audio duration"""
    duration = len(audio) / sample_rate
    if duration < min_duration:
        return (
            False,
            f"Audio is too short (minimum {min_duration} seconds required, got {duration:.2f})",
        )
    return True, None
