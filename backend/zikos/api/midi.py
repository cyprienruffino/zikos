"""MIDI API endpoints"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from zikos.api.validation import validate_uuid
from zikos.services.midi import MidiService

_logger = logging.getLogger(__name__)

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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error validating MIDI")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/{midi_file_id}/synthesize")
async def synthesize_midi(midi_file_id: str, instrument: str = "piano"):
    """Synthesize MIDI to audio"""
    validate_uuid(midi_file_id, "MIDI file ID")
    try:
        audio_file_id = await midi_service.synthesize(midi_file_id, instrument)
        return {"audio_file_id": audio_file_id}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        # Deliberate tool errors (e.g. missing SoundFont) carry actionable messages
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error synthesizing MIDI %s", midi_file_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/{midi_file_id}/render")
async def render_notation(midi_file_id: str, format: str = "sheet_music"):
    """Render MIDI to notation"""
    validate_uuid(midi_file_id, "MIDI file ID")
    try:
        result = await midi_service.render_notation(midi_file_id, format)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error rendering notation for %s", midi_file_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{midi_file_id}")
async def get_midi_file(midi_file_id: str):
    """Get MIDI file"""
    validate_uuid(midi_file_id, "MIDI file ID")
    try:
        file_path = await midi_service.get_midi_path(midi_file_id)
        return FileResponse(file_path, media_type="audio/midi")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"MIDI file {midi_file_id} not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _logger.exception("Unexpected error getting MIDI file %s", midi_file_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e
