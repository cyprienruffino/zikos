"""Chat service"""

import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from zikos.mcp.server import MCPServer
from zikos.services.llm import LLMService

_logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat interactions

    Session state (conversation history) lives in the LLM service's
    conversation manager; this service holds no per-session state itself.
    """

    def __init__(self):
        self.llm_service = LLMService()
        # Share the same UserSettingsService so tool writes are visible to the prompt builder
        self.mcp_server = MCPServer(user_settings_service=self.llm_service.user_settings_service)

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

    async def process_message_stream(
        self,
        message: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Process chat message with streaming"""
        if not session_id:
            session_id = self._create_session()

        yield {"type": "session_id", "session_id": session_id}

        async for chunk in self.llm_service.generate_response_stream(
            message,
            session_id,
            self.mcp_server,
        ):
            chunk["session_id"] = session_id
            yield chunk

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
            _logger.exception("Error handling audio ready for %s", audio_file_id)
            return {
                "type": "error",
                "message": f"Error processing audio: {str(e)}",
                "audio_file_id": audio_file_id,
            }

    async def handle_connect(
        self,
        session_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Trigger a greeting from the LLM when a new session opens."""
        if not session_id:
            session_id = self._create_session()

        yield {"type": "session_id", "session_id": session_id}

        async for chunk in self.llm_service.generate_response_stream(
            "",
            session_id,
            self.mcp_server,
        ):
            chunk["session_id"] = session_id
            yield chunk

    def _create_session(self) -> str:
        """Create new session ID (history is tracked by the conversation manager)"""
        return str(uuid.uuid4())
