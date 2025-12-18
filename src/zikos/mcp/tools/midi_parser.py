"""MIDI parser for simplified format"""

import re
from pathlib import Path
from typing import Any

try:
    from music21 import key, meter, note, stream, tempo
except ImportError:
    note = None
    stream = None
    tempo = None
    meter = None
    key = None


class MidiParseError(Exception):
    """Error parsing MIDI text"""

    pass


def parse_midi_text(midi_text: str) -> dict[str, Any]:
    """Parse simplified MIDI format to structured data"""
    if not note or not stream:
        raise MidiParseError("music21 not available")

    midi_block_pattern = r"\[MIDI\](.*?)\[/MIDI\]"
    match = re.search(midi_block_pattern, midi_text, re.DOTALL)

    if not match:
        raise MidiParseError("No [MIDI]...[/MIDI] block found")

    content = match.group(1).strip()
    lines = [line.strip() for line in content.split("\n") if line.strip()]

    metadata: dict[str, Any] = {
        "tempo": 120,
        "time_signature": "4/4",
        "key": "C major",
    }
    tracks: list[dict[str, Any]] = []
    current_track: dict[str, Any] | None = None

    for line in lines:
        line_lower = line.lower()

        if line_lower.startswith("tempo:"):
            tempo_str = line.split(":", 1)[1].strip()
            try:
                metadata["tempo"] = int(float(tempo_str))
            except ValueError as err:
                raise MidiParseError(f"Invalid tempo: {tempo_str}") from err

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
            note_data = parse_note_line(line)
            if note_data:
                current_track["notes"].append(note_data)

    if current_track:
        tracks.append(current_track)

    if not tracks:
        raise MidiParseError("No tracks found in MIDI data")

    return {"metadata": metadata, "tracks": tracks}


def parse_note_line(line: str) -> dict[str, Any] | None:
    """Parse a note line like 'C4 velocity=60 duration=0.5'"""
    line = line.strip()
    if not line:
        return None

    parts = line.split()
    if not parts:
        return None

    note_name = parts[0]
    velocity = 60
    duration = 0.5

    for part in parts[1:]:
        if part.startswith("velocity="):
            try:
                velocity = int(float(part.split("=", 1)[1]))
            except (ValueError, IndexError):
                pass
        elif part.startswith("duration="):
            try:
                duration = float(part.split("=", 1)[1])
            except (ValueError, IndexError):
                pass

    return {
        "note": note_name,
        "velocity": velocity,
        "duration": duration,
    }


def create_music21_stream(parsed_data: dict[str, Any]) -> Any:
    """Create music21 Stream from parsed MIDI data"""
    if not stream or not note or not tempo or not meter or not key:
        raise MidiParseError("music21 not available")

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
            duration = note_data["duration"]
            velocity = note_data["velocity"]

            try:
                n = note.Note(note_name)
                n.quarterLength = duration
                n.volume.velocity = velocity
                part.append(n)
            except Exception as e:
                raise MidiParseError(f"Invalid note: {note_name} - {str(e)}") from e

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
