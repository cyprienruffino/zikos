"""Recording tools"""

import uuid
from typing import Any


class RecordingTools:
    """Audio recording MCP tools"""

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "request_audio_recording",
                    "description": "Request user to record audio",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string"},
                            "max_duration": {"type": "number", "default": 60.0},
                        },
                        "required": ["prompt"],
                    },
                },
            },
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "request_audio_recording":
            return await self.request_audio_recording(
                kwargs["prompt"],
                kwargs.get("max_duration", 60.0),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def request_audio_recording(self, prompt: str, max_duration: float) -> dict[str, Any]:
        """Request audio recording"""
        recording_id = str(uuid.uuid4())

        return {
            "status": "recording_requested",
            "prompt": prompt,
            "max_duration": max_duration,
            "recording_id": recording_id,
        }
