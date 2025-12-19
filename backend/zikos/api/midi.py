"""MIDI API endpoints"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from zikos.services.midi import MidiService

router = APIRouter()
midi_service = MidiService()


class ValidateMidiRequest(BaseModel):
    """Request model for MIDI validation"""

    midi_text: str


@router.post("/validate")
async def validate_midi(request: ValidateMidiRequest):
    """Validate MIDI text"""
    try:
        result = await midi_service.validate_midi(request.midi_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{midi_file_id}/synthesize")
async def synthesize_midi(midi_file_id: str, instrument: str = "piano"):
    """Synthesize MIDI to audio"""
    try:
        audio_file_id = await midi_service.synthesize(midi_file_id, instrument)
        return {"audio_file_id": audio_file_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{midi_file_id}/render")
async def render_notation(midi_file_id: str, format: str = "both"):
    """Render MIDI to notation"""
    try:
        result = await midi_service.render_notation(midi_file_id, format)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{midi_file_id}")
async def get_midi_file(midi_file_id: str):
    """Get MIDI file"""
    try:
        file_path = await midi_service.get_midi_path(midi_file_id)
        return FileResponse(file_path, media_type="audio/midi")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
