"""Audio service"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from zikos.config import settings
from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.services.audio_preprocessing import AudioPreprocessingService

_logger = logging.getLogger(__name__)


class AudioService:
    """Service for audio storage and analysis"""

    # Baseline analysis results per audio_file_id, shared across instances:
    # the upload endpoint and the LLM service each hold their own
    # AudioService, and both run baseline analysis on the same upload.
    _analysis_cache: dict[str, dict[str, Any]] = {}
    _ANALYSIS_CACHE_MAX_ENTRIES = 64

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

            # Move (not copy): the preprocessed file would otherwise remain in
            # the cache dir forever, doubling storage per upload.
            shutil.move(str(preprocessed_path), str(file_path))
        except ValueError:
            # Validation errors (bad filename/extension) — let callers map to 400
            raise
        except Exception as e:
            _logger.exception("Failed to preprocess and store audio")
            raise RuntimeError(f"Failed to preprocess and store audio: {e}") from e

        return audio_file_id

    async def run_baseline_analysis(self, audio_file_id: str) -> dict[str, Any]:
        """Run baseline analysis tools (cached per audio_file_id)

        The upload endpoint runs baseline analysis at upload time and the LLM
        runs it again when handling audio_ready; caching makes the second
        call free. Stored files are immutable per ID, so no invalidation is
        needed.
        """
        cached = AudioService._analysis_cache.get(audio_file_id)
        if cached is not None:
            return cached

        tempo_result = await self.analysis_tools.analyze_tempo(audio_file_id)
        pitch_result = await self.analysis_tools.detect_pitch(audio_file_id)
        rhythm_result = await self.analysis_tools.analyze_rhythm(audio_file_id)
        instrument_result = await self.analysis_tools.detect_instrument(audio_file_id)

        result = {
            "tempo": tempo_result,
            "pitch": pitch_result,
            "rhythm": rhythm_result,
            "instrument": instrument_result,
        }

        cache = AudioService._analysis_cache
        cache[audio_file_id] = result
        while len(cache) > AudioService._ANALYSIS_CACHE_MAX_ENTRIES:
            cache.pop(next(iter(cache)))
        return result

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
