"""Recording tools"""

import uuid
from typing import Any

from zikos.constants import RECORDING
from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class RecordingTools(ToolCollection):
    """Audio recording MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="request_audio_recording",
                description="Create a recording widget that allows the user to record audio. Use this when you need to hear the student's performance for analysis. The widget provides an interactive recording interface with record/stop/send controls.",
                category=ToolCategory.RECORDING,
                detailed_description="""Create a recording widget that allows the user to record audio.

Returns: dict with status, prompt, max_duration, recording_id

Interpretation Guidelines:
- prompt: Clear instructions for what to record (e.g., 'Please play the C major scale') - be specific
- max_duration: Maximum recording length in seconds - set based on what you're asking for
- recording_id: Unique identifier for this recording request
- Use when you need to hear the student's performance to provide feedback
- Provide clear, specific prompts so students know exactly what to play
- Set appropriate max_duration (scales: 30-60s, pieces: 2-5min, exercises: 60-120s)
- After recording, the audio will be available for analysis using audio analysis tools
- The widget provides an interactive interface with record, stop, and send controls
- Essential for providing personalized feedback based on actual performance
- Combine with audio analysis tools (pitch, rhythm, tempo) after receiving the recording""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "request_audio_recording",
                        "description": "Create a recording widget that allows the user to record audio. Use this when you need to hear the student's performance for analysis. The widget provides an interactive recording interface with record/stop/send controls.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "Instructions for what to record (e.g., 'Please play the C major scale')",
                                },
                                "max_duration": {
                                    "type": "number",
                                    "description": "Maximum recording duration in seconds",
                                    "default": RECORDING.DEFAULT_MAX_DURATION,
                                },
                            },
                            "required": ["prompt"],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "request_audio_recording":
            return await self.request_audio_recording(
                kwargs["prompt"],
                kwargs.get("max_duration", RECORDING.DEFAULT_MAX_DURATION),
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
