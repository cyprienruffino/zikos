"""Tuner tools"""

import uuid
from typing import Any


class TunerTools:
    """Tuner MCP tools"""

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for function calling"""
        return [
            {
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
