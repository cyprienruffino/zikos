"""Audio comparison tools"""

from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio import pitch, rhythm, tempo
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_compare_audio_tool() -> Tool:
    """Get the compare_audio tool definition"""
    return Tool(
        name="compare_audio",
        description="Compare two audio recordings across tempo, pitch, rhythm, or overall performance. Useful for tracking progress between practice sessions or comparing different takes.",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id_1": {"type": "string"},
            "audio_file_id_2": {"type": "string"},
            "comparison_type": {
                "type": "string",
                "enum": ["rhythm", "pitch", "tempo", "overall"],
                "default": "overall",
            },
        },
        required=["audio_file_id_1", "audio_file_id_2"],
        detailed_description="""Compare two audio recordings across tempo, pitch, rhythm, or overall performance.

Returns: dict with comparison_type, similarity_score (0.0-1.0), differences (detailed metrics), improvements (list), regressions (list)

Interpretation Guidelines:
- similarity_score: >0.85 very similar, 0.70-0.85 similar, 0.50-0.70 different, <0.50 very different
- improvements: Areas where audio2 is better than audio1 - acknowledge progress
- regressions: Areas where audio2 is worse than audio1 - address these
- differences: Detailed metrics showing specific differences in tempo, pitch, rhythm
- Use "overall" for general comparison, or specific types ("rhythm", "pitch", "tempo") for focused analysis
- When improvements are present, celebrate progress and identify what worked
- When regressions are present, identify what changed and suggest targeted practice
- Useful for tracking progress over time or comparing different practice approaches
- Combine with comprehensive_analysis on each file for deeper understanding of changes""",
    )


def get_compare_to_reference_tool() -> Tool:
    """Get the compare_to_reference tool definition"""
    return Tool(
        name="compare_to_reference",
        description="Compare audio to a reference (scale, exercise, MIDI file)",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
            "reference_type": {
                "type": "string",
                "enum": ["scale", "midi_file"],
            },
            "reference_params": {
                "type": "object",
                "description": "Parameters for reference (e.g., {'scale': 'C major', 'tempo': 120} or {'midi_file_id': 'midi_123'})",
            },
        },
        required=["audio_file_id", "reference_type"],
        detailed_description="""Compare audio to a reference (scale, exercise, MIDI file).

Returns: dict with reference_type, comparison (metrics), errors (list of wrong notes, timing issues), detected_key (for scale comparison)

Interpretation Guidelines:
- reference_type: "scale" (compare to scale pattern), "midi_file" (compare to MIDI reference)
- comparison: Contains pitch_accuracy, rhythm_accuracy, tempo_match (0.0-1.0 scores)
- errors: List of specific mistakes (wrong notes, timing issues) with timestamps
- For scale comparison: Checks if notes match the scale, detects wrong notes
- For MIDI comparison: Compares tempo, pitch accuracy, and rhythm to the MIDI reference
- When errors are present, use timestamps to identify problem areas
- pitch_accuracy < 0.75 indicates intonation issues or wrong notes
- rhythm_accuracy < 0.75 indicates timing problems
- tempo_match < 0.8 indicates tempo deviation from reference
- Use to provide objective feedback on scale practice, exercises, or pieces with MIDI reference
- Combine errors list with specific timestamps to guide focused practice""",
    )


VALID_COMPARISON_TYPES = ("overall", "tempo", "pitch", "rhythm")


async def compare_audio(
    audio_path_1: str, audio_path_2: str, comparison_type: str
) -> dict[str, Any]:
    """Compare two audio recordings"""
    try:
        if comparison_type not in VALID_COMPARISON_TYPES:
            return {
                "error": True,
                "error_type": "INVALID_COMPARISON_TYPE",
                "message": (
                    f"Unknown comparison_type: '{comparison_type}'. "
                    f"Valid values: {', '.join(VALID_COMPARISON_TYPES)}."
                ),
            }

        # Only run the analyses the requested comparison actually needs.
        tempo_1: dict[str, Any] = {}
        tempo_2: dict[str, Any] = {}
        pitch_1: dict[str, Any] = {}
        pitch_2: dict[str, Any] = {}
        rhythm_1: dict[str, Any] = {}
        rhythm_2: dict[str, Any] = {}

        if comparison_type in ("tempo", "overall"):
            tempo_1 = await tempo.analyze_tempo(audio_path_1)
            tempo_2 = await tempo.analyze_tempo(audio_path_2)
            if tempo_1.get("error") or tempo_2.get("error"):
                return {
                    "error": True,
                    "error_type": "PROCESSING_FAILED",
                    "message": "Failed to analyze one or both audio files",
                }

        if comparison_type in ("pitch", "overall"):
            pitch_1 = await pitch.detect_pitch(audio_path_1)
            pitch_2 = await pitch.detect_pitch(audio_path_2)
            if pitch_1.get("error") or pitch_2.get("error"):
                return {
                    "error": True,
                    "error_type": "PROCESSING_FAILED",
                    "message": "Failed to analyze pitch in one or both audio files",
                }

        if comparison_type in ("rhythm", "overall"):
            rhythm_1 = await rhythm.analyze_rhythm(audio_path_1)
            rhythm_2 = await rhythm.analyze_rhythm(audio_path_2)
            if rhythm_1.get("error") or rhythm_2.get("error"):
                return {
                    "error": True,
                    "error_type": "PROCESSING_FAILED",
                    "message": "Failed to analyze rhythm in one or both audio files",
                }

        differences: dict[str, Any] = {}
        improvements: list[str] = []
        regressions: list[str] = []
        similarity_metrics: list[float] = []

        if comparison_type in ("tempo", "overall"):
            bpm_1 = tempo_1.get("bpm", 0)
            bpm_2 = tempo_2.get("bpm", 0)
            tempo_diff = abs(bpm_1 - bpm_2)
            tempo_stability_1 = tempo_1.get("tempo_stability_score", 0)
            tempo_stability_2 = tempo_2.get("tempo_stability_score", 0)

            similarity_metrics.append(max(0.0, 1.0 - (tempo_diff / 20.0)))

            differences["tempo"] = {
                "audio1": bpm_1,
                "audio2": bpm_2,
                "difference": tempo_diff,
                "stability_audio1": tempo_stability_1,
                "stability_audio2": tempo_stability_2,
            }

            if tempo_stability_2 > tempo_stability_1 + 0.05:
                improvements.append("tempo_stability")
            elif tempo_stability_2 < tempo_stability_1 - 0.05:
                regressions.append("tempo_stability")

        if comparison_type in ("pitch", "overall"):
            intonation_1 = pitch_1.get("intonation_accuracy") or 0
            intonation_2 = pitch_2.get("intonation_accuracy") or 0
            stability_1 = pitch_1.get("pitch_stability") or 0
            stability_2 = pitch_2.get("pitch_stability") or 0

            similarity_metrics.append(max(0.0, 1.0 - abs(intonation_2 - intonation_1)))
            similarity_metrics.append(max(0.0, 1.0 - abs(stability_2 - stability_1)))

            differences["pitch_accuracy"] = {
                "audio1": intonation_1,
                "audio2": intonation_2,
                "improvement": intonation_2 - intonation_1,
            }

            differences["pitch_stability"] = {
                "audio1": stability_1,
                "audio2": stability_2,
                "improvement": stability_2 - stability_1,
            }

            if intonation_2 > intonation_1 + 0.05:
                improvements.append("pitch_accuracy")
            elif intonation_2 < intonation_1 - 0.05:
                regressions.append("pitch_accuracy")

            if stability_2 > stability_1 + 0.05:
                improvements.append("pitch_stability")
            elif stability_2 < stability_1 - 0.05:
                regressions.append("pitch_stability")

        if comparison_type in ("rhythm", "overall"):
            timing_1 = rhythm_1.get("timing_accuracy") or 0
            timing_2 = rhythm_2.get("timing_accuracy") or 0
            avg_dev_1 = rhythm_1.get("average_deviation_ms") or 0
            avg_dev_2 = rhythm_2.get("average_deviation_ms") or 0

            similarity_metrics.append(max(0.0, 1.0 - abs(timing_2 - timing_1)))

            differences["rhythm_accuracy"] = {
                "audio1": timing_1,
                "audio2": timing_2,
                "improvement": timing_2 - timing_1,
            }

            differences["timing_deviation"] = {
                "audio1": avg_dev_1,
                "audio2": avg_dev_2,
                "improvement": avg_dev_1 - avg_dev_2,
            }

            if timing_2 > timing_1 + 0.05:
                improvements.append("rhythm_accuracy")
            elif timing_2 < timing_1 - 0.05:
                regressions.append("rhythm_accuracy")

        # Per-type similarity: average of the metrics gathered for the
        # requested comparison type (all of them for "overall").
        similarity_score = (
            sum(similarity_metrics) / len(similarity_metrics) if similarity_metrics else 0.0
        )

        return {
            "comparison_type": comparison_type,
            "similarity_score": float(similarity_score),
            "differences": differences,
            "improvements": improvements,
            "regressions": regressions,
        }

    except FileNotFoundError as e:
        return {
            "error": True,
            "error_type": "FILE_NOT_FOUND",
            "message": str(e),
        }
    except Exception as e:
        return {
            "error": True,
            "error_type": "PROCESSING_FAILED",
            "message": f"Comparison failed: {str(e)}",
        }


async def compare_to_reference(
    audio_path: str, reference_type: str, reference_params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compare audio to a reference (scale, exercise, MIDI file)"""
    try:
        if reference_params is None:
            reference_params = {}

        audio_tempo = await tempo.analyze_tempo(audio_path)
        audio_pitch = await pitch.detect_pitch(audio_path)
        audio_rhythm = await rhythm.analyze_rhythm(audio_path)

        if audio_tempo.get("error") or audio_pitch.get("error") or audio_rhythm.get("error"):
            return {
                "error": True,
                "error_type": "PROCESSING_FAILED",
                "message": "Failed to analyze audio file",
            }

        comparison: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []

        # Accept 'midi' as an alias for 'midi_file'
        if reference_type == "midi":
            reference_type = "midi_file"

        if reference_type == "scale":
            scale_name = reference_params.get("scale", "C major")
            detected_key = audio_pitch.get("detected_key", "unknown")

            try:
                scale_pitch_classes = _get_scale_pitch_classes(scale_name)
            except ValueError as e:
                return {
                    "error": True,
                    "error_type": "INVALID_KEY",
                    "message": str(e),
                }

            comparison["pitch_accuracy"] = audio_pitch.get("intonation_accuracy", 0)
            comparison["rhythm_accuracy"] = audio_rhythm.get("timing_accuracy", 0)

            expected_tempo = reference_params.get("tempo", None)
            if expected_tempo:
                actual_tempo = audio_tempo.get("bpm", 0)
                tempo_match = 1.0 - min(1.0, abs(actual_tempo - expected_tempo) / 20.0)
                comparison["tempo_match"] = float(tempo_match)
            else:
                comparison["tempo_match"] = None
                comparison["tempo_match_note"] = (
                    "No reference tempo provided, so tempo match was not measured."
                )

            notes = audio_pitch.get("notes", [])
            for note_data in notes:
                note_name = note_data.get("pitch", "")
                note_base = note_name.rstrip("0123456789")
                pitch_class = _note_name_to_pitch_class(note_base)
                if pitch_class is not None and pitch_class not in scale_pitch_classes:
                    errors.append(
                        {
                            "time": note_data.get("start_time", 0),
                            "type": "wrong_note",
                            "expected": f"note in {scale_name}",
                            "played": note_name,
                        }
                    )

            return {
                "reference_type": "scale",
                "scale": scale_name,
                "comparison": comparison,
                "errors": errors,
                "detected_key": detected_key,
            }

        elif reference_type == "midi_file":
            midi_file_id = reference_params.get("midi_file_id")
            if not midi_file_id:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "midi_file_id is required for MIDI reference comparison",
                }

            from zikos.mcp.tools.processing import MidiTools

            midi_tools = MidiTools()
            try:
                midi_path = midi_tools.storage_path / f"{midi_file_id}.mid"
                if not midi_path.exists():
                    return {
                        "error": True,
                        "error_type": "FILE_NOT_FOUND",
                        "message": f"MIDI file {midi_file_id} not found",
                    }

                from music21 import midi

                score = midi.translate.midiFilePathToStream(str(midi_path))
                if score is None:
                    return {
                        "error": True,
                        "error_type": "PROCESSING_FAILED",
                        "message": "Failed to parse MIDI file",
                    }

                midi_tempo = None
                try:
                    metronome_marks = score.metronomeMarkBoundaries()
                    if metronome_marks and len(metronome_marks) > 0:
                        mark = metronome_marks[0][2]
                        if hasattr(mark, "number"):
                            midi_tempo = mark.number
                except Exception:
                    pass

                if midi_tempo:
                    actual_tempo = audio_tempo.get("bpm", 0)
                    tempo_match = 1.0 - min(1.0, abs(actual_tempo - midi_tempo) / 20.0)
                    comparison["tempo_match"] = float(tempo_match)
                else:
                    comparison["tempo_match"] = None
                    comparison["tempo_match_note"] = (
                        "MIDI reference has no tempo marking, so tempo match was not measured."
                    )

                # intonation/timing of the audio itself, independent of the reference
                comparison["intonation_accuracy"] = audio_pitch.get("intonation_accuracy", 0)
                comparison["rhythm_accuracy"] = audio_rhythm.get("timing_accuracy", 0)

                # Note-level comparison against the MIDI reference
                played_notes = audio_pitch.get("notes", [])
                try:
                    reference_notes = _extract_midi_note_sequence(score)
                except Exception as e:
                    reference_notes = None
                    comparison["note_comparison_note"] = (
                        f"Could not extract notes from the MIDI reference ({e}); "
                        "note-level comparison was not performed."
                    )

                if reference_notes is not None:
                    alignment = _align_note_sequences(reference_notes, played_notes)
                    comparison["pitch_accuracy"] = alignment["pitch_accuracy"]
                    comparison["matched_notes"] = alignment["matched"]
                    comparison["reference_note_count"] = len(reference_notes)
                    comparison["played_note_count"] = len(played_notes)
                    errors.extend(alignment["errors"])
                else:
                    comparison["pitch_accuracy"] = None

                return {
                    "reference_type": "midi_file",
                    "midi_file_id": midi_file_id,
                    "comparison": comparison,
                    "errors": errors,
                }

            except Exception as e:
                return {
                    "error": True,
                    "error_type": "PROCESSING_FAILED",
                    "message": f"MIDI comparison failed: {str(e)}",
                }

        else:
            return {
                "error": True,
                "error_type": "INVALID_REFERENCE_TYPE",
                "message": f"Unknown reference_type: {reference_type}. Supported: 'scale', 'midi_file'",
            }

    except FileNotFoundError as e:
        return {
            "error": True,
            "error_type": "FILE_NOT_FOUND",
            "message": str(e),
        }
    except Exception as e:
        return {
            "error": True,
            "error_type": "PROCESSING_FAILED",
            "message": f"Reference comparison failed: {str(e)}",
        }


def _get_scale_pitch_classes(scale_name: str) -> set[int]:
    """Get the pitch classes (0-11) of a scale using music21.

    Handles flat keys ("Bb major"), sharp keys, and minor mode.
    Raises ValueError for unknown keys/modes.
    """
    from music21 import key as m21_key

    parts = scale_name.strip().split()
    if not parts:
        raise ValueError("Empty scale name. Expected e.g. 'C major', 'Bb major', 'A minor'.")

    tonic = parts[0]
    mode = parts[1].lower() if len(parts) > 1 else "major"

    # music21 uses '-' for flats: "Bb" -> "B-"
    tonic_m21 = tonic[0].upper() + tonic[1:].replace("b", "-") if len(tonic) > 1 else tonic.upper()

    try:
        k = m21_key.Key(tonic_m21, mode)
        return {p.pitchClass for p in k.pitches}
    except Exception as e:
        raise ValueError(
            f"Unknown scale '{scale_name}'. Expected a tonic (e.g. C, F#, Bb) "
            f"optionally followed by a mode (major, minor): {e}"
        ) from e


def _note_name_to_pitch_class(note_base: str) -> int | None:
    """Convert a note name without octave (e.g. 'A#', 'Bb') to a pitch class (0-11)"""
    if not note_base:
        return None
    from music21 import pitch as m21_pitch

    try:
        return int(m21_pitch.Pitch(note_base.replace("b", "-")).pitchClass)
    except Exception:
        return None


def _extract_midi_note_sequence(score: Any) -> list[dict[str, Any]]:
    """Extract an ordered note sequence from a music21 score.

    Returns a list of {"name": str, "midi": int, "offset_quarters": float}.
    For chords, the highest pitch (usually the melody) is used.
    """
    reference_notes = []
    for element in score.flatten().notes:
        pitches = list(element.pitches)
        if not pitches:
            continue
        top = max(pitches, key=lambda p: p.midi)
        reference_notes.append(
            {
                "name": top.nameWithOctave.replace("-", "b"),
                "midi": int(top.midi),
                "offset_quarters": float(element.offset),
            }
        )
    reference_notes.sort(key=lambda n: n["offset_quarters"])
    return reference_notes


def _align_note_sequences(
    reference_notes: list[dict[str, Any]], played_notes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Align the detected note sequence to the MIDI reference.

    Uses difflib sequence matching on pitch classes (octave-insensitive, so an
    octave error in pitch detection does not cascade into all-wrong notes).
    Returns pitch_accuracy, matched count, and per-note errors with timestamps.
    """
    import difflib

    errors: list[dict[str, Any]] = []

    ref_classes = [n["midi"] % 12 for n in reference_notes]
    played_classes = []
    for n in played_notes:
        note_base = str(n.get("pitch", "")).rstrip("0123456789")
        pc = _note_name_to_pitch_class(note_base)
        played_classes.append(pc if pc is not None else -1)

    matcher = difflib.SequenceMatcher(a=ref_classes, b=played_classes, autojunk=False)
    matched = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            matched += i2 - i1
        elif tag == "replace":
            for offset in range(max(i2 - i1, j2 - j1)):
                ref_note = reference_notes[i1 + offset] if i1 + offset < i2 else None
                played_note = played_notes[j1 + offset] if j1 + offset < j2 else None
                if ref_note and played_note:
                    errors.append(
                        {
                            "time": played_note.get("start_time", 0),
                            "type": "wrong_note",
                            "expected": ref_note["name"],
                            "played": played_note.get("pitch", ""),
                        }
                    )
                elif ref_note:
                    errors.append(
                        {
                            "time": None,
                            "type": "missed_note",
                            "expected": ref_note["name"],
                        }
                    )
                elif played_note:
                    errors.append(
                        {
                            "time": played_note.get("start_time", 0),
                            "type": "extra_note",
                            "played": played_note.get("pitch", ""),
                        }
                    )
        elif tag == "delete":
            for idx in range(i1, i2):
                errors.append(
                    {
                        "time": None,
                        "type": "missed_note",
                        "expected": reference_notes[idx]["name"],
                    }
                )
        elif tag == "insert":
            for idx in range(j1, j2):
                errors.append(
                    {
                        "time": played_notes[idx].get("start_time", 0),
                        "type": "extra_note",
                        "played": played_notes[idx].get("pitch", ""),
                    }
                )

    denominator = max(len(reference_notes), len(played_notes))
    pitch_accuracy = float(matched / denominator) if denominator > 0 else None

    return {
        "pitch_accuracy": pitch_accuracy,
        "matched": matched,
        "errors": errors,
    }
