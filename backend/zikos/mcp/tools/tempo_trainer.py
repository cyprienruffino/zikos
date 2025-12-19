"""Tempo trainer tools"""

import uuid
from typing import Any


class TempoTrainerTools:
    """Tempo trainer MCP tools"""

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_tempo_trainer",
                    "description": "Create a tempo trainer widget that gradually increases or decreases tempo over time. Useful for building speed or maintaining accuracy at higher tempos.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_bpm": {
                                "type": "number",
                                "description": "Starting tempo in BPM",
                                "default": 60,
                            },
                            "end_bpm": {
                                "type": "number",
                                "description": "Target tempo in BPM",
                                "default": 120,
                            },
                            "duration_minutes": {
                                "type": "number",
                                "description": "Duration of the tempo ramp in minutes",
                                "default": 5.0,
                            },
                            "time_signature": {
                                "type": "string",
                                "description": "Time signature (e.g., '4/4', '3/4')",
                                "default": "4/4",
                            },
                            "ramp_type": {
                                "type": "string",
                                "enum": ["linear", "exponential"],
                                "description": "Type of tempo ramp: 'linear' for constant increase, 'exponential' for gradual start then faster increase",
                                "default": "linear",
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
        if tool_name == "create_tempo_trainer":
            return await self.create_tempo_trainer(
                kwargs.get("start_bpm", 60),
                kwargs.get("end_bpm", 120),
                kwargs.get("duration_minutes", 5.0),
                kwargs.get("time_signature", "4/4"),
                kwargs.get("ramp_type", "linear"),
                kwargs.get("description"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def create_tempo_trainer(
        self,
        start_bpm: float,
        end_bpm: float,
        duration_minutes: float,
        time_signature: str,
        ramp_type: str,
        description: str | None,
    ) -> dict[str, Any]:
        """Create tempo trainer widget"""
        trainer_id = str(uuid.uuid4())

        return {
            "status": "tempo_trainer_created",
            "trainer_id": trainer_id,
            "start_bpm": start_bpm,
            "end_bpm": end_bpm,
            "duration_minutes": duration_minutes,
            "time_signature": time_signature,
            "ramp_type": ramp_type,
            "description": description,
        }
