"""Audio service"""

import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from src.zikos.config import settings
from src.zikos.mcp.tools import audio as audio_tools_module


class AudioService:
    """Service for audio storage and analysis"""

    def __init__(self):
        self.storage_path = Path(settings.audio_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.analysis_tools = audio_tools_module.AudioAnalysisTools()

    async def store_audio(self, file: UploadFile, recording_id: str = None) -> str:
        """Store uploaded audio file"""
        audio_file_id = str(uuid.uuid4())
        file_path = self.storage_path / f"{audio_file_id}.wav"

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return audio_file_id

    async def run_baseline_analysis(self, audio_file_id: str) -> dict[str, Any]:
        """Run baseline analysis tools"""
        file_path = self.storage_path / f"{audio_file_id}.wav"

        tempo_result = await self.analysis_tools.analyze_tempo(str(file_path))
        pitch_result = await self.analysis_tools.detect_pitch(str(file_path))
        rhythm_result = await self.analysis_tools.analyze_rhythm(str(file_path))

        return {
            "tempo": tempo_result,
            "pitch": pitch_result,
            "rhythm": rhythm_result,
        }

    async def get_audio_info(self, audio_file_id: str) -> dict[str, Any]:
        """Get audio file information"""
        file_path = self.storage_path / f"{audio_file_id}.wav"

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file {audio_file_id} not found")

        return await self.analysis_tools.get_audio_info(str(file_path))

    async def get_audio_path(self, audio_file_id: str) -> Path:
        """Get audio file path"""
        file_path = self.storage_path / f"{audio_file_id}.wav"

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file {audio_file_id} not found")

        return file_path
