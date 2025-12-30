"""Chat API endpoints"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from zikos.services.chat import ChatService

router = APIRouter()
chat_service = ChatService()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat"""
    try:
        await websocket.accept()
    except Exception as e:
        print(f"Error accepting WebSocket connection: {e}")
        return

    try:
        while True:
            data = await websocket.receive_json()

            if data["type"] == "message":
                try:
                    # Check if streaming is requested
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
                    print(f"Error processing message: {e}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Error processing message: {str(e)}",
                        }
                    )

            elif data["type"] == "audio_ready":
                try:
                    response = await chat_service.handle_audio_ready(
                        data["audio_file_id"],
                        data.get("recording_id"),
                        data.get("session_id"),
                    )
                    await websocket.send_json(response)
                except Exception as e:
                    print(f"Error handling audio ready: {e}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Error handling audio: {str(e)}",
                        }
                    )

            elif data["type"] == "get_thinking":
                try:
                    response = chat_service.get_thinking(data.get("session_id"))
                    await websocket.send_json(response)
                except Exception as e:
                    print(f"Error getting thinking: {e}")
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

    except WebSocketDisconnect:
        await chat_service.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"WebSocket error: {str(e)}",
                }
            )
        except Exception:
            pass
