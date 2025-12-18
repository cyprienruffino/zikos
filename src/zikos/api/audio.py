"""Audio API endpoints"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.zikos.services.audio import AudioService

router = APIRouter()
audio_service = AudioService()


@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    recording_id: str | None = File(None),
):
    """Upload audio file"""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{audio_file_id}/info")
async def get_audio_info(audio_file_id: str):
    """Get audio file information"""
    try:
        info = await audio_service.get_audio_info(audio_file_id)
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{audio_file_id}")
async def get_audio_file(audio_file_id: str):
    """Get audio file"""
    try:
        file_path = await audio_service.get_audio_path(audio_file_id)
        from fastapi.responses import FileResponse

        return FileResponse(file_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
