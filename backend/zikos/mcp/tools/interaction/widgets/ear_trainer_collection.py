"""Ear trainer tools"""

import uuid
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class EarTrainerTools(ToolCollection):
    """Ear trainer MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="create_ear_trainer",
                description="Create an ear training widget for interval or chord recognition. Plays intervals/chords and helps users develop their ear.",
                category=ToolCategory.WIDGET,
                detailed_description="""Create an ear training widget for interval or chord recognition.

Returns: dict with status, trainer_id, mode, difficulty, root_note, description

Interpretation Guidelines:
- mode: "intervals" for interval recognition, "chords" for chord recognition
- difficulty: "easy" (perfect intervals), "medium" (major/minor), "hard" (all intervals including augmented/diminished)
- root_note: Starting note for intervals/chords (e.g., 'C', 'A') - use to focus on specific keys
- Use to develop students' aural skills and pitch recognition
- Start with "easy" difficulty and progress to "hard" as skills improve
- "intervals" mode helps with melodic recognition, "chords" mode helps with harmonic recognition
- The widget provides interactive training with immediate feedback
- Regular ear training improves intonation, sight-reading, and musical understanding
- Combine with specific practice goals in the description field""",
                schema={
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
            ),
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
