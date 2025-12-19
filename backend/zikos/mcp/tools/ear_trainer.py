"""Ear trainer tools"""

import uuid
from typing import Any


class EarTrainerTools:
    """Ear trainer MCP tools"""

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_ear_trainer",
                    "description": "Create an ear training widget for interval or chord recognition. Plays intervals/chords and helps users develop their ear.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mode": {
                                "type": "string",
                                "enum": ["intervals", "chords"],
                                "description": "Training mode: 'intervals' for interval recognition, 'chords' for chord recognition",
                                "default": "intervals",
                            },
                            "difficulty": {
                                "type": "string",
                                "enum": ["easy", "medium", "hard"],
                                "description": "Difficulty level: 'easy' (perfect intervals), 'medium' (major/minor intervals), 'hard' (all intervals including augmented/diminished)",
                                "default": "medium",
                            },
                            "root_note": {
                                "type": "string",
                                "description": "Root note for intervals/chords (e.g., 'C', 'A')",
                                "default": "C",
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
        if tool_name == "create_ear_trainer":
            return await self.create_ear_trainer(
                kwargs.get("mode", "intervals"),
                kwargs.get("difficulty", "medium"),
                kwargs.get("root_note", "C"),
                kwargs.get("description"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def create_ear_trainer(
        self,
        mode: str,
        difficulty: str,
        root_note: str,
        description: str | None,
    ) -> dict[str, Any]:
        """Create ear trainer widget"""
        trainer_id = str(uuid.uuid4())

        return {
            "status": "ear_trainer_created",
            "trainer_id": trainer_id,
            "mode": mode,
            "difficulty": difficulty,
            "root_note": root_note,
            "description": description,
        }
