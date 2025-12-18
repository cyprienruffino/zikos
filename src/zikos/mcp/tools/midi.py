"""MIDI tools"""

import uuid
from pathlib import Path
from typing import Any

from src.zikos.config import settings
from src.zikos.mcp.tools.midi_parser import MidiParseError, midi_text_to_file


class MidiTools:
    """MIDI processing MCP tools"""

    def __init__(self):
        self.storage_path = Path(settings.midi_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "validate_midi",
                    "description": "Validate MIDI text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "midi_text": {"type": "string"},
                        },
                        "required": ["midi_text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "midi_to_audio",
                    "description": "Synthesize MIDI to audio",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "midi_file_id": {"type": "string"},
                            "instrument": {"type": "string", "default": "piano"},
                        },
                        "required": ["midi_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "midi_to_notation",
                    "description": "Render MIDI to notation",
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
            from src.zikos.mcp.tools.midi_parser import parse_midi_text

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
            raise FileNotFoundError(f"MIDI file {midi_file_id} not found")

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
            from src.zikos.config import settings

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
            from src.zikos.config import settings

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
            raise FileNotFoundError(f"MIDI file {midi_file_id} not found")

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
