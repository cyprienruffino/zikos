"""MIDI tools"""

import uuid
from pathlib import Path
from typing import Any

from zikos.config import settings
from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection
from zikos.mcp.tools.processing.midi.midi_parser import MidiParseError, midi_text_to_file


class MidiTools(ToolCollection):
    """MIDI processing MCP tools"""

    def __init__(self):
        self.storage_path = Path(settings.midi_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="validate_midi",
                description="Validate MIDI text syntax and convert it to a MIDI file. Use this after generating MIDI in your response to ensure it's valid before synthesizing to audio or rendering notation. Returns validation errors if the MIDI syntax is invalid.",
                category=ToolCategory.MIDI,
                detailed_description="""Validate MIDI text syntax and convert it to a MIDI file.

Returns: dict with valid (bool), midi_file_id (str, empty if invalid), errors (list[str]), warnings (list[str]), metadata (dict with duration, tempo, tracks, note_count)

Interpretation Guidelines:
- valid: True if MIDI syntax is correct and file was created, False if there are syntax errors
- midi_file_id: Use this ID with midi_to_audio or midi_to_notation if valid=True
- errors: Specific syntax errors that need to be fixed - address these before retrying
- warnings: Non-fatal issues that don't prevent file creation but may affect playback
- metadata: Information about the MIDI content (duration, tempo, number of tracks, note count)
- Always call this tool after generating MIDI text to ensure it's valid before using midi_to_audio or midi_to_notation
- If valid=False, fix the errors and regenerate the MIDI text
- Check metadata to verify the MIDI matches your expectations (duration, tempo, etc.)""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "validate_midi",
                        "description": """Validate MIDI text syntax and convert it to a MIDI file. Use this after generating MIDI in your response to ensure it's valid before synthesizing to audio or rendering notation.

Returns: dict with:
- valid (bool): True if MIDI is valid, False otherwise
- midi_file_id (str): UUID of created MIDI file (empty string if invalid)
- errors (list[str]): List of validation error messages (empty if valid)
- warnings (list[str]): List of warnings (non-fatal issues)
- metadata (dict): Parsed metadata including duration, tempo, tracks, note_count

Error Handling:
- If valid=False, check errors list for specific issues. Fix the MIDI syntax and try again.
- If valid=True, use the returned midi_file_id with midi_to_audio or midi_to_notation.""",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "midi_text": {"type": "string"},
                            },
                            "required": ["midi_text"],
                        },
                    },
                },
            ),
            Tool(
                name="midi_to_audio",
                description="Synthesize MIDI file to playable audio. Converts a validated MIDI file into audio that can be played back. Use this after validate_midi to create audio examples for the student.",
                category=ToolCategory.MIDI,
                detailed_description="""Synthesize MIDI file to playable audio.

Returns: dict with audio_file_id (str), midi_file_id (str), instrument (str), duration (float), synthesis_method (str)

Interpretation Guidelines:
- audio_file_id: Use this ID to play the audio or use with other audio analysis tools
- instrument: One of "piano", "guitar", "violin", "bass", "drums" - choose based on the musical context
- duration: Length of generated audio in seconds - verify it matches expected length
- synthesis_method: "fluidsynth" - indicates the synthesis engine used
- Must call validate_midi first to get a valid midi_file_id
- The generated audio can be played back to students or used with audio analysis tools
- Different instruments work better for different musical contexts (piano for melodies, guitar for chords, etc.)
- If synthesis fails, check that FluidSynth and SoundFont are properly installed on the system""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "midi_to_audio",
                        "description": """Synthesize MIDI file to playable audio. Converts a validated MIDI file into audio that can be played back. Use this after validate_midi to create audio examples for the student.

Returns: dict with:
- audio_file_id (str): UUID of generated audio file
- midi_file_id (str): The MIDI file ID that was synthesized
- instrument (str): Instrument used for synthesis
- duration (float): Duration of generated audio in seconds
- synthesis_method (str): Method used ("fluidsynth")

Available instruments: "piano", "guitar", "violin", "bass", "drums"

Error Handling:
- If MIDI file not found: You must call validate_midi first to create the MIDI file
- If synthesis fails: Check that FluidSynth and SoundFont are properly installed""",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "midi_file_id": {"type": "string"},
                                "instrument": {
                                    "type": "string",
                                    "default": "piano",
                                    "enum": ["piano", "guitar", "violin", "bass", "drums"],
                                    "description": "Instrument to use for synthesis. Available: piano, guitar, violin, bass, drums",
                                },
                            },
                            "required": ["midi_file_id"],
                        },
                    },
                },
            ),
            Tool(
                name="midi_to_notation",
                description="Render MIDI file to musical notation (sheet music and/or tabs). Generates visual notation that students can see and read. Use this after validate_midi to provide visual reference alongside audio examples.",
                category=ToolCategory.MIDI,
                detailed_description="""Render MIDI file to musical notation (sheet music and/or tabs).

Returns: dict with midi_file_id (str), format (str), sheet_music_url (str, optional), tabs_url (str, optional), sheet_music_error (str, optional), tabs_error (str, optional)

Interpretation Guidelines:
- format: "sheet_music", "tabs", or "both" - choose based on student's reading preference
- sheet_music_url: URL to sheet music image - use "both" or "sheet_music" format
- tabs_url: URL to tabs image - use "both" or "tabs" format
- sheet_music_error/tabs_error: Error messages if rendering failed - check these if URLs are missing
- Must call validate_midi first to get a valid midi_file_id
- Use "both" to provide both notation types for maximum accessibility
- Sheet music is better for traditional notation readers, tabs are better for guitar/bass players
- Visual notation helps students understand the structure and practice reading music
- Combine with midi_to_audio to provide both visual and audio examples""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "midi_to_notation",
                        "description": """Render MIDI file to musical notation (sheet music and/or tabs). Generates visual notation that students can see and read. Use this after validate_midi to provide visual reference alongside audio examples.

Returns: dict with:
- midi_file_id (str): The MIDI file ID that was rendered
- format (str): Requested format ("sheet_music", "tabs", or "both")
- sheet_music_url (str, optional): URL to sheet music image (if format includes "sheet_music")
- tabs_url (str, optional): URL to tabs image (if format includes "tabs")
- sheet_music_error (str, optional): Error message if sheet music generation failed
- tabs_error (str, optional): Error message if tabs generation failed

Error Handling:
- If MIDI file not found: You must call validate_midi first to create the MIDI file
- If rendering fails: Check sheet_music_error or tabs_error fields for details""",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "midi_file_id": {"type": "string"},
                                "format": {"type": "string", "default": "both"},
                            },
                            "required": ["midi_file_id"],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "validate_midi":
            return await self.validate_midi(kwargs["midi_text"])
        elif tool_name == "midi_to_audio":
            return await self.midi_to_audio(
                kwargs["midi_file_id"], kwargs.get("instrument", "piano")
            )
        elif tool_name == "midi_to_notation":
            return await self.midi_to_notation(kwargs["midi_file_id"], kwargs.get("format", "both"))
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def validate_midi(self, midi_text: str) -> dict[str, Any]:
        """Validate MIDI text and convert to MIDI file"""
        errors: list[str] = []
        warnings: list[str] = []
        metadata: dict[str, Any] = {}

        try:
            from zikos.mcp.tools.processing.midi.midi_parser import parse_midi_text

            parsed_data = parse_midi_text(midi_text)
            metadata = parsed_data.get("metadata", {})

            midi_file_id = str(uuid.uuid4())
            midi_path = self.storage_path / f"{midi_file_id}.mid"

            midi_text_to_file(midi_text, midi_path)

            if not midi_path.exists() or midi_path.stat().st_size == 0:
                errors.append("Failed to create MIDI file")
                return {
                    "valid": False,
                    "midi_file_id": "",
                    "errors": errors,
                    "warnings": warnings,
                    "metadata": metadata,
                }

            return {
                "valid": True,
                "midi_file_id": midi_file_id,
                "errors": errors,
                "warnings": warnings,
                "metadata": metadata,
            }

        except MidiParseError as e:
            errors.append(str(e))
            return {
                "valid": False,
                "midi_file_id": "",
                "errors": errors,
                "warnings": warnings,
                "metadata": metadata,
            }
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
            return {
                "valid": False,
                "midi_file_id": "",
                "errors": errors,
                "warnings": warnings,
                "metadata": metadata,
            }

    async def midi_to_audio(self, midi_file_id: str, instrument: str) -> dict[str, Any]:
        """Synthesize MIDI to audio using FluidSynth"""
        midi_path = self.storage_path / f"{midi_file_id}.mid"

        if not midi_path.exists():
            raise FileNotFoundError(
                f"MIDI file '{midi_file_id}' not found. "
                "You must first call 'validate_midi' with MIDI text to create a MIDI file. "
                "The validate_midi tool will return a midi_file_id that you can then use with midi_to_audio."
            )

        soundfont_path = self._find_soundfont()
        if not soundfont_path:
            raise RuntimeError(
                "No SoundFont found. Please install a SoundFont (e.g., FluidR3_GM.sf2)"
            )

        try:
            return await self._synthesize_with_cli(midi_path, soundfont_path, instrument)
        except (FileNotFoundError, ImportError):
            return await self._synthesize_with_pyfluidsynth(midi_path, soundfont_path, instrument)

    async def _synthesize_with_cli(
        self, midi_path: Path, soundfont_path: Path, instrument: str
    ) -> dict[str, Any]:
        """Synthesize using fluidsynth CLI (preferred method)"""
        import shutil
        import subprocess
        import tempfile

        import soundfile as sf

        fluidsynth_cmd = shutil.which("fluidsynth")
        if not fluidsynth_cmd:
            raise FileNotFoundError("fluidsynth CLI not found")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name

        try:
            result = subprocess.run(
                [
                    fluidsynth_cmd,
                    "-F",
                    str(tmp_wav_path),
                    "-n",
                    "-i",
                    str(soundfont_path),
                    str(midi_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"FluidSynth synthesis failed: {result.stderr}")

            if not Path(tmp_wav_path).exists():
                raise RuntimeError("FluidSynth did not generate output file")

            audio_data, sample_rate = sf.read(tmp_wav_path)

            audio_file_id = str(uuid.uuid4())
            from zikos.config import settings

            audio_storage = Path(settings.audio_storage_path)
            audio_storage.mkdir(parents=True, exist_ok=True)
            audio_path = audio_storage / f"{audio_file_id}.wav"

            sf.write(str(audio_path), audio_data, sample_rate)

            duration = len(audio_data) / sample_rate

            return {
                "audio_file_id": audio_file_id,
                "midi_file_id": midi_path.stem,
                "instrument": instrument,
                "duration": duration,
                "synthesis_method": "fluidsynth",
            }

        finally:
            if Path(tmp_wav_path).exists():
                Path(tmp_wav_path).unlink()

    async def _synthesize_with_pyfluidsynth(
        self, midi_path: Path, soundfont_path: Path, instrument: str
    ) -> dict[str, Any]:
        """Synthesize using pyfluidsynth Python bindings"""
        try:
            import fluidsynth
            import numpy as np
            import soundfile as sf
        except ImportError as e:
            raise ImportError(f"pyfluidsynth not available: {e}") from e

        from music21 import midi

        midi_stream = midi.translate.midiFilePathToStream(str(midi_path))
        if midi_stream is None:
            raise ValueError("Failed to parse MIDI file")

        fs = fluidsynth.Synth()
        fs.start()

        try:
            sfid = fs.sfload(str(soundfont_path))
            if sfid == -1:
                raise RuntimeError(f"Failed to load SoundFont: {soundfont_path}")

            fs.program_select(0, sfid, 0, self._instrument_to_program(instrument))

            sample_rate = 44100
            audio_chunks = []

            for element in midi_stream.flat.notes:
                if hasattr(element, "pitch"):
                    pitch_midi = element.pitch.midi
                    duration = float(element.duration.quarterLength)
                    velocity = 60

                    if hasattr(element, "volume") and hasattr(element.volume, "velocity"):
                        velocity = element.volume.velocity

                    fs.noteon(0, pitch_midi, velocity)
                    samples = int(duration * sample_rate)
                    audio_chunk = fs.get_samples(samples)
                    audio_chunks.append(audio_chunk)
                    fs.noteoff(0, pitch_midi)

            if not audio_chunks:
                raise ValueError("No audio data generated from MIDI")

            audio_array = np.concatenate(audio_chunks)
            audio_array = audio_array.astype(np.float32) / 32768.0

            audio_file_id = str(uuid.uuid4())
            from zikos.config import settings

            audio_storage = Path(settings.audio_storage_path)
            audio_storage.mkdir(parents=True, exist_ok=True)
            audio_path = audio_storage / f"{audio_file_id}.wav"

            sf.write(str(audio_path), audio_array, sample_rate)

            duration = len(audio_array) / sample_rate

            return {
                "audio_file_id": audio_file_id,
                "midi_file_id": midi_path.stem,
                "instrument": instrument,
                "duration": duration,
                "synthesis_method": "fluidsynth",
            }

        finally:
            fs.delete()

    async def midi_to_notation(self, midi_file_id: str, format: str) -> dict[str, Any]:
        """Render MIDI to notation using music21"""
        midi_path = self.storage_path / f"{midi_file_id}.mid"

        if not midi_path.exists():
            raise FileNotFoundError(
                f"MIDI file '{midi_file_id}' not found. "
                "You must first call 'validate_midi' with MIDI text to create a MIDI file. "
                "The validate_midi tool will return a midi_file_id that you can then use with midi_to_notation."
            )

        try:
            from music21 import midi

            score = midi.translate.midiFilePathToStream(str(midi_path))
            if score is None:
                raise ValueError("Failed to parse MIDI file")

            notation_path = Path(settings.notation_storage_path)
            notation_path.mkdir(parents=True, exist_ok=True)

            result: dict[str, Any] = {
                "midi_file_id": midi_file_id,
                "format": format,
            }

            if format in ("sheet_music", "both"):
                sheet_path = notation_path / f"sheet_{midi_file_id}.png"
                try:
                    score.write("musicxml.png", fp=str(sheet_path))
                    if sheet_path.exists():
                        result["sheet_music_url"] = f"/notation/sheet_{midi_file_id}.png"
                    else:
                        result["sheet_music_error"] = "Failed to generate sheet music image"
                except Exception as e:
                    result["sheet_music_error"] = str(e)

            if format in ("tabs", "both"):
                tabs_path = notation_path / f"tabs_{midi_file_id}.png"
                try:
                    score.write("musicxml.png", fp=str(tabs_path))
                    if tabs_path.exists():
                        result["tabs_url"] = f"/notation/tabs_{midi_file_id}.png"
                    else:
                        result["tabs_error"] = "Failed to generate tabs image"
                except Exception as e:
                    result["tabs_error"] = str(e)

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to render notation: {str(e)}") from e

    def _find_soundfont(self) -> Path | None:
        """Find system SoundFont"""
        common_paths = [
            Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
            Path("/usr/share/sounds/sf2/default.sf2"),
            Path("/usr/local/share/sounds/sf2/FluidR3_GM.sf2"),
            Path.home() / ".local/share/sounds/sf2/FluidR3_GM.sf2",
        ]

        for path in common_paths:
            if path.exists():
                return path

        import shutil

        fluidsynth_path = shutil.which("fluidsynth")
        if fluidsynth_path:
            default_sf2 = Path("/usr/share/sounds/sf2/default.sf2")
            if default_sf2.exists():
                return default_sf2

        return None

    def _instrument_to_program(self, instrument: str) -> int:
        """Convert instrument name to MIDI program number"""
        instrument_map: dict[str, int] = {
            "piano": 0,
            "guitar": 24,
            "violin": 40,
            "bass": 32,
            "drums": 128,
        }
        return instrument_map.get(instrument.lower(), 0)
