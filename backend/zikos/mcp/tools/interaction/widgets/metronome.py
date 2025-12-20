"""Metronome tools"""

import uuid
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class MetronomeTools(ToolCollection):
    """Metronome MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="create_metronome",
                description="Create a metronome widget that plays a beat pattern. The metronome can play while the user is recording or playing their instrument.",
                category=ToolCategory.WIDGET,
                schema={
                    "type": "function",
                    "function": {
                        "name": "create_metronome",
                        "description": "Create a metronome widget that plays a beat pattern. The metronome can play while the user is recording or playing their instrument.",
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
        metronome_id = str(uuid.uuid4())

        return {
            "status": "metronome_created",
            "metronome_id": metronome_id,
            "bpm": bpm,
            "time_signature": time_signature,
            "description": description,
        }
