"""MIDI parser for simplified format"""

import re
from pathlib import Path
from typing import Any

from music21 import chord, key, meter, note, stream, tempo


class MidiParseError(Exception):
    """Error parsing MIDI text"""

    pass


_FORMAT_HINT = (
    "Required format:\n"
    "[MIDI]\n"
    "Tempo: 120\n"
    "Time Signature: 4/4\n"
    "Key: C major\n"
    "Track 1:\n"
    "  C4 velocity=60 duration=1.0\n"
    "  E4 velocity=60 duration=1.0\n"
    "[/MIDI]\n"
    "Notes: use names like C4, D#5, Bb3. Duration is in quarter notes (1.0=quarter, 2.0=half, 0.5=eighth)."
)


def parse_midi_text(midi_text: str) -> dict[str, Any]:
    """Parse simplified MIDI format to structured data.

    Returns {"metadata": ..., "tracks": ..., "warnings": [...]}.
    """
    midi_block_pattern = r"\[MIDI\](.*?)\[/MIDI\]"
    match = re.search(midi_block_pattern, midi_text, re.DOTALL | re.IGNORECASE)

    if not match:
        raise MidiParseError(f"No [MIDI]...[/MIDI] block found. {_FORMAT_HINT}")

    content = match.group(1).strip()
    lines = [line.strip() for line in content.split("\n") if line.strip()]

    metadata: dict[str, Any] = {
        "tempo": 120,
        "time_signature": "4/4",
        "key": "C major",
    }
    tracks: list[dict[str, Any]] = []
    current_track: dict[str, Any] | None = None
    warnings: list[str] = []

    for line in lines:
        line_lower = line.lower()

        if line_lower.startswith("tempo:"):
            tempo_str = line.split(":", 1)[1].strip()
            try:
                tempo_value = float(tempo_str)
            except ValueError as err:
                raise MidiParseError(f"Invalid tempo: {tempo_str}") from err
            if tempo_value <= 0:
                raise MidiParseError(f"Tempo must be positive, got: {tempo_str}")
            # Keep fractional tempi (e.g. 72.5), but report clean ints as ints
            metadata["tempo"] = int(tempo_value) if tempo_value.is_integer() else tempo_value

        elif line_lower.startswith("time signature:") or line_lower.startswith("time sig:"):
            ts_str = line.split(":", 1)[1].strip()
            metadata["time_signature"] = ts_str

        elif line_lower.startswith("key:"):
            key_str = line.split(":", 1)[1].strip()
            metadata["key"] = key_str

        elif line_lower.startswith("track"):
            if current_track:
                tracks.append(current_track)
            track_match = re.match(r"track\s+(\d+)(?:\s*\(([^)]+)\))?:", line, re.IGNORECASE)
            track_num = int(track_match.group(1)) if track_match else 1
            track_name = (
                track_match.group(2).strip() if track_match and track_match.group(2) else None
            )
            current_track = {
                "number": track_num,
                "name": track_name,
                "notes": [],
            }

        elif current_track is not None:
            note_data = parse_note_line(line, warnings)
            if note_data:
                current_track["notes"].append(note_data)

    if current_track:
        tracks.append(current_track)

    if not tracks:
        raise MidiParseError(
            "No tracks found in MIDI data. "
            "Add a 'Track N:' line before your notes, e.g.:\n"
            "  Track 1:\n"
            "    C4 velocity=60 duration=1.0"
        )

    return {"metadata": metadata, "tracks": tracks, "warnings": warnings}


def parse_note_line(line: str, warnings: list[str] | None = None) -> dict[str, Any] | None:
    """Parse a note line like 'C4 velocity=60 duration=0.5'.

    Chord lines with several pitches ('C4 E4 G4 velocity=60 duration=1.0')
    are supported: all pitches share the velocity/duration.

    Malformed velocity=/duration= values raise MidiParseError instead of
    silently falling back to defaults. Out-of-range velocities are clamped
    to 0-127 with a warning appended to `warnings`.
    """
    if warnings is None:
        warnings = []

    line = line.strip()
    if not line:
        return None

    parts = line.split()
    if not parts:
        return None

    pitches: list[str] = []
    velocity = 60
    duration = 0.5

    for part in parts:
        if part.startswith("velocity="):
            value = part.split("=", 1)[1]
            try:
                velocity = int(float(value))
            except (ValueError, IndexError) as err:
                raise MidiParseError(
                    f"Invalid velocity '{value}' in line '{line}'. "
                    "Velocity must be a number between 0 and 127 (e.g. velocity=80)."
                ) from err
            if velocity < 0 or velocity > 127:
                clamped = max(0, min(127, velocity))
                warnings.append(
                    f"Velocity {velocity} out of range in line '{line}'; clamped to {clamped}."
                )
                velocity = clamped
        elif part.startswith("duration="):
            value = part.split("=", 1)[1]
            try:
                duration = float(value)
            except (ValueError, IndexError) as err:
                raise MidiParseError(
                    f"Invalid duration '{value}' in line '{line}'. "
                    "Duration must be a positive number in quarter notes "
                    "(e.g. duration=0.5 for an eighth note)."
                ) from err
            if duration <= 0:
                raise MidiParseError(
                    f"Duration must be greater than 0, got '{value}' in line '{line}'."
                )
        elif "=" in part:
            warnings.append(f"Ignoring unknown attribute '{part}' in line '{line}'.")
        else:
            pitches.append(part)

    if not pitches:
        warnings.append(f"Line '{line}' has no note name; skipped.")
        return None

    if len(pitches) > 1:
        warnings.append(f"Line '{line}' contains {len(pitches)} pitches; interpreted as a chord.")

    return {
        "note": pitches[0],
        "pitches": pitches,
        "velocity": velocity,
        "duration": duration,
    }


def create_music21_stream(parsed_data: dict[str, Any]) -> Any:
    """Create music21 Stream from parsed MIDI data"""
    metadata = parsed_data["metadata"]
    tracks = parsed_data["tracks"]

    score = stream.Score()

    for track_data in tracks:
        part = stream.Part()
        track_name = track_data.get("name")
        if track_name:
            part.partName = track_name

        for note_data in track_data["notes"]:
            note_name = note_data["note"]
            pitches = note_data.get("pitches", [note_name])
            duration = note_data["duration"]
            velocity = note_data["velocity"]

            if note_name.lower() == "rest":
                r = note.Rest()
                r.quarterLength = duration
                part.append(r)
                continue

            try:
                if len(pitches) > 1:
                    element: note.Note | chord.Chord = chord.Chord(pitches)
                else:
                    element = note.Note(note_name)
                element.quarterLength = duration
                element.volume.velocity = velocity
                part.append(element)
            except Exception as e:
                raise MidiParseError(
                    f"Invalid note name '{note_name if len(pitches) <= 1 else ' '.join(pitches)}'. "
                    "Use standard note names like C4, D#5, Bb3, or 'rest'. "
                    f"Original error: {str(e)}"
                ) from e

        if len(part.notes) > 0:
            score.append(part)

    if len(score.parts) == 0:
        raise MidiParseError("No valid notes found")

    tempo_obj = tempo.MetronomeMark(number=metadata["tempo"])
    score.insert(0, tempo_obj)

    try:
        time_sig = meter.TimeSignature(metadata["time_signature"])
        score.insert(0, time_sig)
    except Exception:
        pass

    try:
        key_obj = key.Key(metadata["key"])
        score.insert(0, key_obj)
    except Exception:
        pass

    return score


def midi_text_to_file(midi_text: str, output_path: Path) -> None:
    """Convert MIDI text to MIDI file"""
    parsed_data = parse_midi_text(midi_text)
    score = create_music21_stream(parsed_data)
    score.write("midi", fp=str(output_path))
