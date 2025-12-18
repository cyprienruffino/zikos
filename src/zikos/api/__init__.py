"""API routes"""

from fastapi import APIRouter

from src.zikos.api import audio, chat, midi

router = APIRouter(prefix="/api")

router.include_router(audio.router, prefix="/audio", tags=["audio"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(midi.router, prefix="/midi", tags=["midi"])
