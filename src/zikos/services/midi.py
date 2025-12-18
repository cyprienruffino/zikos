"""MIDI service"""

from pathlib import Path
from typing import Any

from src.zikos.config import settings
from src.zikos.mcp.tools import midi as midi_tools_module


class MidiService:
    """Service for MIDI processing"""

    def __init__(self):
        self.storage_path = Path(settings.midi_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.notation_path = Path(settings.notation_storage_path)
        self.notation_path.mkdir(parents=True, exist_ok=True)
        self.midi_tools = midi_tools_module.MidiTools()

    async def validate_midi(self, midi_text: str) -> dict[str, Any]:
        """Validate MIDI text"""
        return await self.midi_tools.validate_midi(midi_text)

    async def synthesize(self, midi_file_id: str, instrument: str) -> str:
        """Synthesize MIDI to audio"""
        result = await self.midi_tools.midi_to_audio(midi_file_id, instrument)
        audio_file_id: str = result.get("audio_file_id", "")
        return audio_file_id

    async def render_notation(self, midi_file_id: str, format: str) -> dict[str, Any]:
        """Render MIDI to notation"""
        result = await self.midi_tools.midi_to_notation(midi_file_id, format)
        return result

    async def get_midi_path(self, midi_file_id: str) -> Path:
        """Get MIDI file path"""
        file_path = self.storage_path / f"{midi_file_id}.mid"

        if not file_path.exists():
            raise FileNotFoundError(f"MIDI file {midi_file_id} not found")

        return file_path
