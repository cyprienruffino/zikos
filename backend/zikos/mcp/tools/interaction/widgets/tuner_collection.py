"""Tuner tools"""

import uuid
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class TunerTools(ToolCollection):
    """Tuner MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="create_tuner",
                description="Create a tuner widget that detects pitch in real-time. Useful for tuning instruments before recording or practicing intonation.",
                category=ToolCategory.WIDGET,
                detailed_description="""Create a tuner widget that detects pitch in real-time.

Returns: dict with status, tuner_id, reference_frequency, note, octave, description

Interpretation Guidelines:
- reference_frequency: Standard tuning frequency (440Hz for A4, 432Hz for A432 tuning)
- note: Target note name (e.g., 'A', 'E', 'C') - helps with visual display
- octave: Target octave (e.g., 4 for A4) - helps with visual display
- Use before recording to ensure instruments are in tune
- Use for intonation practice, especially for string instruments
- Standard tuning is 440Hz (A4), but some styles use 432Hz or other tunings
- The widget provides real-time visual feedback showing how close the pitch is to the target
- Essential for string instruments (guitar, violin, etc.) and wind instruments
- Combine with intonation analysis tools to track improvement over time""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "create_tuner",
                        "description": "Create a tuner widget that detects pitch in real-time. Useful for tuning instruments before recording or practicing intonation.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "reference_frequency": {
                                    "type": "number",
                                    "description": "Reference frequency in Hz (e.g., 440 for A4, 432 for A432 tuning)",
                                    "default": 440.0,
                                },
                                "note": {
                                    "type": "string",
                                    "description": "Target note name (e.g., 'A', 'E', 'C') - optional, helps with visual display",
                                },
                                "octave": {
                                    "type": "number",
                                    "description": "Target octave (e.g., 4 for A4) - optional",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional instruction or context for the user",
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
        if tool_name == "create_tuner":
            return await self.create_tuner(
                kwargs.get("reference_frequency", 440.0),
                kwargs.get("note"),
                kwargs.get("octave"),
                kwargs.get("description"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def create_tuner(
        self,
        reference_frequency: float,
        note: str | None,
        octave: int | None,
        description: str | None,
    ) -> dict[str, Any]:
        """Create tuner widget"""
        tuner_id = str(uuid.uuid4())

        return {
            "status": "tuner_created",
            "tuner_id": tuner_id,
            "reference_frequency": reference_frequency,
            "note": note,
            "octave": octave,
            "description": description,
        }
