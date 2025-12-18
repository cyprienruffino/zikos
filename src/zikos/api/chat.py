"""Chat API endpoints"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.zikos.services.chat import ChatService

router = APIRouter()
chat_service = ChatService()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "message":
                response = await chat_service.process_message(
                    data["message"],
                    data.get("session_id"),
                )
                await websocket.send_json(response)

            elif data["type"] == "audio_ready":
                response = await chat_service.handle_audio_ready(
                    data["audio_file_id"],
                    data.get("recording_id"),
                    data.get("session_id"),
                )
                await websocket.send_json(response)

            elif data["type"] == "cancel_recording":
                await websocket.send_json(
                    {
                        "type": "recording_cancelled",
                        "recording_id": data.get("recording_id"),
                    }
                )

    except WebSocketDisconnect:
        await chat_service.disconnect(websocket)
