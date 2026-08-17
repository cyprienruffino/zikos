"""Chat API endpoints"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from zikos.services.chat import ChatService

_logger = logging.getLogger(__name__)

router = APIRouter()
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """Get or create ChatService instance (lazy initialization)"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat"""
    try:
        await websocket.accept()
    except Exception as e:
        _logger.error(f"Error accepting WebSocket connection: {e}")
        return

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except (ValueError, TypeError) as e:
                # Malformed JSON frame — report and keep the connection alive
                _logger.warning(f"Received malformed WebSocket frame: {e}")
                await websocket.send_json(
                    {"type": "error", "message": "Invalid frame: expected a JSON object"}
                )
                continue

            if not isinstance(data, dict) or not isinstance(data.get("type"), str):
                await websocket.send_json(
                    {"type": "error", "message": "Invalid frame: missing string 'type' field"}
                )
                continue

            if data["type"] == "connect":
                try:
                    chat_service = get_chat_service()
                    async for chunk in chat_service.handle_connect(data.get("session_id")):
                        await websocket.send_json(chunk)
                except Exception as e:
                    _logger.error(f"Error handling connect: {e}")
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif data["type"] == "message":
                if not isinstance(data.get("message"), str):
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid frame: missing string 'message'"}
                    )
                    continue
                try:
                    # Check if streaming is requested
                    chat_service = get_chat_service()
                    if data.get("stream", False):
                        async for chunk in chat_service.process_message_stream(
                            data["message"],
                            data.get("session_id"),
                        ):
                            await websocket.send_json(chunk)
                    else:
                        response = await chat_service.process_message(
                            data["message"],
                            data.get("session_id"),
                        )
                        await websocket.send_json(response)
                except Exception as e:
                    _logger.error(f"Error processing message: {e}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Error processing message: {str(e)}",
                        }
                    )

            elif data["type"] == "audio_ready":
                if not isinstance(data.get("audio_file_id"), str) or not data["audio_file_id"]:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Invalid frame: missing string 'audio_file_id'",
                        }
                    )
                    continue
                try:
                    chat_service = get_chat_service()
                    response = await chat_service.handle_audio_ready(
                        data["audio_file_id"],
                        data.get("recording_id"),
                        data.get("session_id"),
                    )
                    await websocket.send_json(response)
                except Exception as e:
                    _logger.error(f"Error handling audio ready: {e}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Error handling audio: {str(e)}",
                        }
                    )

            elif data["type"] == "get_thinking":
                try:
                    chat_service = get_chat_service()
                    response = chat_service.get_thinking(data.get("session_id"))
                    await websocket.send_json(response)
                except Exception as e:
                    _logger.error(f"Error getting thinking: {e}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Error getting thinking: {str(e)}",
                        }
                    )

            elif data["type"] == "cancel_recording":
                await websocket.send_json(
                    {
                        "type": "recording_cancelled",
                        "recording_id": data.get("recording_id"),
                    }
                )

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown frame type: {data['type']!r}",
                    }
                )

    except WebSocketDisconnect:
        chat_service = get_chat_service()
        await chat_service.disconnect(websocket)
    except Exception as e:
        _logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"WebSocket error: {str(e)}",
                }
            )
        except Exception:
            pass
