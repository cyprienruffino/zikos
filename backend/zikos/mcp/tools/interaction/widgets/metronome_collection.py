"""Metronome tools"""

import re
import uuid
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection

MIN_BPM = 20
MAX_BPM = 400
TIME_SIGNATURE_PATTERN = re.compile(r"^\d{1,2}/(1|2|4|8|16|32)$")


class MetronomeTools(ToolCollection):
    """Metronome MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="create_metronome",
                description="Create a metronome widget with built-in recording controls. The user can start the metronome, then record directly from the widget. No need to use request_audio_recording separately when a metronome is active.",
                category=ToolCategory.DISPLAY_WIDGET,
                detailed_description="""Create a metronome widget with built-in recording controls.

The widget includes:
- Metronome playback (play/pause/stop) with visual beat indicators
- Recording controls (record/stop/send/cancel) embedded in the widget
- A checkbox (checked by default) to keep the metronome playing during recording

When this widget is active, do NOT use request_audio_recording separately.
The user can record directly from the metronome widget.

Returns: dict with status, metronome_id, bpm, time_signature, description

Interpretation Guidelines:
- bpm: Beats per minute (tempo) - choose based on piece requirements or practice goals
- time_signature: Musical time signature (e.g., '4/4', '3/4', '6/8') - affects beat emphasis
- Use for rhythm practice, maintaining steady tempo, and recording with consistent timing
- Start at slower tempos for learning, gradually increase as proficiency improves
- Different time signatures emphasize different beats (4/4 emphasizes beat 1, 3/4 emphasizes beat 1)
- Combine with rhythm analysis tools to track timing improvement""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "create_metronome",
                        "description": "Create a metronome widget with built-in recording controls. The user can start the metronome, then record directly from the widget. No need to use request_audio_recording separately when a metronome is active.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "bpm": {
                                    "type": "number",
                                    "description": "Beats per minute (tempo)",
                                    "default": 120,
                                },
                                "time_signature": {
                                    "type": "string",
                                    "description": "Time signature (e.g., '4/4', '3/4', '6/8')",
                                    "default": "4/4",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional description or instruction for the user",
                                },
                            },
                            "required": [],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "create_metronome":
            return await self.create_metronome(
                kwargs.get("bpm", 120),
                kwargs.get("time_signature", "4/4"),
                kwargs.get("description"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def create_metronome(
        self, bpm: float, time_signature: str, description: str | None
    ) -> dict[str, Any]:
        """Create metronome widget"""
        if not isinstance(bpm, int | float) or not (MIN_BPM <= bpm <= MAX_BPM):
            return {
                "error": True,
                "error_type": "INVALID_PARAMETER",
                "message": f"bpm must be a number between {MIN_BPM} and {MAX_BPM}, got: {bpm}",
            }
        if not isinstance(time_signature, str) or not TIME_SIGNATURE_PATTERN.match(time_signature):
            return {
                "error": True,
                "error_type": "INVALID_PARAMETER",
                "message": (
                    f"time_signature must look like '4/4', '3/4', or '6/8', got: {time_signature}"
                ),
            }

        metronome_id = str(uuid.uuid4())

        return {
            "status": "metronome_created",
            "metronome_id": metronome_id,
            "bpm": bpm,
            "time_signature": time_signature,
            "description": description,
        }
