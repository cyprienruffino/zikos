"""Audio comparison tools"""

from typing import Any

from zikos.mcp.tools.analysis.audio import pitch, rhythm, tempo
from zikos.mcp.tools.analysis.audio.utils import resolve_audio_path


async def compare_audio(
    audio_path_1: str, audio_path_2: str, comparison_type: str
) -> dict[str, Any]:
    """Compare two audio recordings"""
    try:
        tempo_1 = await tempo.analyze_tempo(audio_path_1)
        tempo_2 = await tempo.analyze_tempo(audio_path_2)
        pitch_1 = await pitch.detect_pitch(audio_path_1)
        pitch_2 = await pitch.detect_pitch(audio_path_2)
        rhythm_1 = await rhythm.analyze_rhythm(audio_path_1)
        rhythm_2 = await rhythm.analyze_rhythm(audio_path_2)

        if tempo_1.get("error") or tempo_2.get("error"):
            return {
                "error": True,
                "error_type": "PROCESSING_FAILED",
                "message": "Failed to analyze one or both audio files",
            }

        if pitch_1.get("error") or pitch_2.get("error"):
            return {
                "error": True,
                "error_type": "PROCESSING_FAILED",
                "message": "Failed to analyze pitch in one or both audio files",
            }

        if rhythm_1.get("error") or rhythm_2.get("error"):
            return {
                "error": True,
                "error_type": "PROCESSING_FAILED",
                "message": "Failed to analyze rhythm in one or both audio files",
            }

        differences: dict[str, Any] = {}
        improvements: list[str] = []
        regressions: list[str] = []

        if comparison_type in ("tempo", "overall"):
            bpm_1 = tempo_1.get("bpm", 0)
            bpm_2 = tempo_2.get("bpm", 0)
            tempo_diff = abs(bpm_1 - bpm_2)
            tempo_stability_1 = tempo_1.get("tempo_stability_score", 0)
            tempo_stability_2 = tempo_2.get("tempo_stability_score", 0)

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
            intonation_1 = pitch_1.get("intonation_accuracy", 0)
            intonation_2 = pitch_2.get("intonation_accuracy", 0)
            stability_1 = pitch_1.get("pitch_stability", 0)
            stability_2 = pitch_2.get("pitch_stability", 0)

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
            timing_1 = rhythm_1.get("timing_accuracy", 0)
            timing_2 = rhythm_2.get("timing_accuracy", 0)
            avg_dev_1 = rhythm_1.get("average_deviation_ms", 0)
            avg_dev_2 = rhythm_2.get("average_deviation_ms", 0)

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

        similarity_score = 0.0
        if comparison_type == "overall":
            metrics = []
            if "tempo" in differences:
                tempo_diff = differences["tempo"]["difference"]
                tempo_similarity = max(0.0, 1.0 - (tempo_diff / 20.0))
                metrics.append(tempo_similarity)

            if "pitch_accuracy" in differences:
                pitch_diff = abs(differences["pitch_accuracy"]["improvement"])
                pitch_similarity = max(0.0, 1.0 - pitch_diff)
                metrics.append(pitch_similarity)

            if "rhythm_accuracy" in differences:
                rhythm_diff = abs(differences["rhythm_accuracy"]["improvement"])
                rhythm_similarity = max(0.0, 1.0 - rhythm_diff)
                metrics.append(rhythm_similarity)

            if metrics:
                similarity_score = sum(metrics) / len(metrics)

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

        if reference_type == "scale":
            scale_name = reference_params.get("scale", "C major")
            expected_key = scale_name.split()[0] if " " in scale_name else scale_name
            detected_key = audio_pitch.get("detected_key", "unknown")

            comparison["pitch_accuracy"] = audio_pitch.get("intonation_accuracy", 0)
            comparison["rhythm_accuracy"] = audio_rhythm.get("timing_accuracy", 0)

            expected_tempo = reference_params.get("tempo", None)
            if expected_tempo:
                actual_tempo = audio_tempo.get("bpm", 0)
                tempo_match = 1.0 - min(1.0, abs(actual_tempo - expected_tempo) / 20.0)
                comparison["tempo_match"] = float(tempo_match)
            else:
                comparison["tempo_match"] = 1.0

            notes = audio_pitch.get("notes", [])
            if notes:
                expected_notes = _get_scale_notes(expected_key)
                for note_data in notes:
                    note_name = note_data.get("pitch", "")
                    note_base = note_name.rstrip("0123456789")
                    if note_base not in expected_notes:
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
                    comparison["tempo_match"] = 1.0

                comparison["pitch_accuracy"] = audio_pitch.get("intonation_accuracy", 0)
                comparison["rhythm_accuracy"] = audio_rhythm.get("timing_accuracy", 0)

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


def _get_scale_notes(key: str) -> list[str]:
    """Get note names for a major scale"""
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    major_intervals = [0, 2, 4, 5, 7, 9, 11]

    try:
        key_idx = note_names.index(key.upper())
        scale_notes = [note_names[(key_idx + interval) % 12] for interval in major_intervals]
        return scale_notes
    except ValueError:
        return note_names
