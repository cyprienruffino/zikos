"""Audio API endpoints"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

_logger = logging.getLogger(__name__)

from zikos.api.validation import validate_uuid
from zikos.constants import UploadConstants
from zikos.services.audio import AudioService

router = APIRouter()
audio_service = AudioService()

_READ_CHUNK_SIZE = 1024 * 1024  # 1 MB


def _validate_upload_type(file: UploadFile) -> None:
    """Validate extension and content-type against the audio allowlist (415 on failure)."""
    extension = Path(file.filename or "").suffix.lower()
    if extension not in UploadConstants.ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(UploadConstants.ALLOWED_AUDIO_EXTENSIONS))
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension {extension!r}. Allowed: {allowed}",
        )

    content_type = (file.content_type or "").lower()
    if content_type and not (
        content_type.startswith(UploadConstants.ALLOWED_CONTENT_TYPE_PREFIXES)
        or content_type in UploadConstants.ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type {content_type!r}",
        )


async def _enforce_upload_size(file: UploadFile) -> None:
    """Read the upload in chunks to enforce the max size (413 on failure)."""
    size = 0
    while chunk := await file.read(_READ_CHUNK_SIZE):
        size += len(chunk)
        if size > UploadConstants.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    "Upload too large. Maximum size is "
                    f"{UploadConstants.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
                ),
            )
    await file.seek(0)


@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    recording_id: str | None = Form(None),
):
    """Upload audio file"""
    _validate_upload_type(file)
    await _enforce_upload_size(file)

    try:
        audio_file_id = await audio_service.store_audio(file, recording_id)
        analysis = await audio_service.run_baseline_analysis(audio_file_id)

        return JSONResponse(
            {
                "audio_file_id": audio_file_id,
                "recording_id": recording_id,
                "analysis": analysis,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error handling audio upload")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{audio_file_id}/info")
async def get_audio_info(audio_file_id: str):
    """Get audio file information"""
    validate_uuid(audio_file_id, "audio file ID")
    try:
        info = await audio_service.get_audio_info(audio_file_id)
        return info
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Audio file {audio_file_id} not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error getting audio info for %s", audio_file_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{audio_file_id}")
async def get_audio_file(audio_file_id: str):
    """Get audio file"""
    validate_uuid(audio_file_id, "audio file ID")
    try:
        file_path = await audio_service.get_audio_path(audio_file_id)
        from fastapi.responses import FileResponse

        return FileResponse(file_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Audio file {audio_file_id} not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error getting audio file %s", audio_file_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e
