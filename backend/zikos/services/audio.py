"""Audio service"""

import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.services.audio_preprocessing import AudioPreprocessingService


class AudioService:
    """Service for audio storage and analysis"""

    def __init__(self):
        self.storage_path = Path(settings.audio_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.analysis_tools = AudioAnalysisTools()
        self.preprocessing_service = AudioPreprocessingService()

    async def store_audio(self, file: UploadFile, recording_id: str | None = None) -> str:
        """Store uploaded audio file with preprocessing"""
        audio_file_id = str(uuid.uuid4())

        try:
            preprocessed_path = await self.preprocessing_service.preprocess_upload_file(
                file, target_format="wav", target_sample_rate=44100
            )

            file_path = self.storage_path / f"{audio_file_id}.wav"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            import shutil

            shutil.copy2(preprocessed_path, file_path)
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise RuntimeError(f"Failed to preprocess and store audio: {e}") from e

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
        result = await self.analysis_tools.get_audio_info(audio_file_id)
        return dict(result)

    async def get_audio_path(self, audio_file_id: str) -> Path:
        """Get audio file path"""
        file_path = self.storage_path / f"{audio_file_id}.wav"

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file {audio_file_id} not found")

        return file_path
