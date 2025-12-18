"""Audio service"""

import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from src.zikos.config import settings
from src.zikos.mcp.tools.audio import AudioAnalysisTools


class AudioService:
    """Service for audio storage and analysis"""

    def __init__(self):
        self.storage_path = Path(settings.audio_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.analysis_tools = AudioAnalysisTools()

    async def store_audio(self, file: UploadFile, recording_id: str | None = None) -> str:
        """Store uploaded audio file"""
        audio_file_id = str(uuid.uuid4())
        file_path = self.storage_path / f"{audio_file_id}.wav"

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return audio_file_id

    async def run_baseline_analysis(self, audio_file_id: str) -> dict[str, Any]:
        """Run baseline analysis tools"""
        tempo_result = await self.analysis_tools.analyze_tempo(audio_file_id)
        pitch_result = await self.analysis_tools.detect_pitch(audio_file_id)
        rhythm_result = await self.analysis_tools.analyze_rhythm(audio_file_id)

        return {
            "tempo": tempo_result,
            "pitch": pitch_result,
            "rhythm": rhythm_result,
        }

    async def get_audio_info(self, audio_file_id: str) -> dict[str, Any]:
        """Get audio file information"""
        return await self.analysis_tools.get_audio_info(audio_file_id)

    async def get_audio_path(self, audio_file_id: str) -> Path:
        """Get audio file path"""
        file_path = self.storage_path / f"{audio_file_id}.wav"

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file {audio_file_id} not found")

        return file_path
