"""Chat service"""

from typing import Any

from fastapi import WebSocket

from zikos.mcp.server import MCPServer
from zikos.services.llm import LLMService


class ChatService:
    """Service for chat interactions"""

    def __init__(self):
        self.llm_service = LLMService()
        self.mcp_server = MCPServer()
        self.sessions: dict[str, dict[str, Any]] = {}

    async def process_message(
        self,
        message: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Process chat message"""
        if not session_id:
            session_id = self._create_session()

        response = await self.llm_service.generate_response(
            message,
            session_id,
            self.mcp_server,
        )

        response["session_id"] = session_id
        return dict(response)

    def get_thinking(self, session_id: str | None) -> dict[str, Any]:
        """Get thinking messages for a session (for debugging)"""
        if not session_id:
            return {"error": "session_id required"}
        return {"thinking": self.llm_service.get_thinking_for_session(session_id)}

    async def handle_audio_ready(
        self,
        audio_file_id: str,
        recording_id: str | None,
        session_id: str | None,
    ) -> dict[str, Any]:
        """Handle audio ready notification"""
        try:
            response = await self.llm_service.handle_audio_ready(
                audio_file_id,
                recording_id,
                session_id,
                self.mcp_server,
            )

            # Ensure response has correct structure
            if isinstance(response, dict) and "type" in response:
                response["audio_file_id"] = audio_file_id
                return response
            else:
                # Handle case where response is just a string
                return {
                    "type": "response",
                    "message": str(response) if response else "Audio analysis complete.",
                    "audio_file_id": audio_file_id,
                }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error processing audio: {str(e)}",
                "audio_file_id": audio_file_id,
            }

    def _create_session(self) -> str:
        """Create new session"""
        import uuid

        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {"messages": []}
        return session_id

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnect"""
        pass
