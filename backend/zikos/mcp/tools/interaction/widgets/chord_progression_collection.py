"""Chord progression tools"""

import uuid
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class ChordProgressionTools(ToolCollection):
    """Chord progression MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="create_chord_progression",
                description="Create a chord progression player widget that loops chord progressions as backing. Useful for practicing scales, improvisation, or rhythm work.",
                category=ToolCategory.WIDGET,
                detailed_description="""Create a chord progression player widget that loops chord progressions as backing.

Returns: dict with status, progression_id, chords, tempo, time_signature, chords_per_bar, instrument, description

Interpretation Guidelines:
- chords: Array of chord names (e.g., ['C', 'G', 'Am', 'F'] or ['I', 'V', 'vi', 'IV'])
- tempo: BPM for the progression - choose based on practice goals (slower for learning, faster for performance)
- time_signature: Musical time signature (e.g., '4/4', '3/4', '6/8')
- chords_per_bar: How many chords per bar - 1 is most common, 2 for faster changes
- instrument: Sound of the chords ('piano', 'guitar', 'strings') - choose based on musical style
- Use for scale practice, improvisation exercises, rhythm practice, or song accompaniment
- Common progressions: I-V-vi-IV (C-G-Am-F), vi-IV-I-V (Am-F-C-G), I-vi-IV-V (C-Am-F-G)
- The widget loops automatically, allowing students to practice over the progression
- Combine with practice instructions in the description field""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "create_chord_progression",
                        "description": "Create a chord progression player widget that loops chord progressions as backing. Useful for practicing scales, improvisation, or rhythm work.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "chords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Array of chord names (e.g., ['C', 'G', 'Am', 'F'] or ['I', 'V', 'vi', 'IV'])",
                                },
                                "tempo": {
                                    "type": "number",
                                    "description": "Tempo in BPM",
                                    "default": 120,
                                },
                                "time_signature": {
                                    "type": "string",
                                    "description": "Time signature (e.g., '4/4', '3/4')",
                                    "default": "4/4",
                                },
                                "chords_per_bar": {
                                    "type": "number",
                                    "description": "Number of chords per bar",
                                    "default": 1,
                                },
                                "instrument": {
                                    "type": "string",
                                    "description": "Instrument for chord playback (e.g., 'piano', 'guitar', 'strings')",
                                    "default": "piano",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Optional instruction or context for the user",
                                },
                            },
                            "required": ["chords"],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "create_chord_progression":
            return await self.create_chord_progression(
                kwargs["chords"],
                kwargs.get("tempo", 120),
                kwargs.get("time_signature", "4/4"),
                kwargs.get("chords_per_bar", 1),
                kwargs.get("instrument", "piano"),
                kwargs.get("description"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def create_chord_progression(
        self,
        chords: list[str],
        tempo: float,
        time_signature: str,
        chords_per_bar: int,
        instrument: str,
        description: str | None,
    ) -> dict[str, Any]:
        """Create chord progression widget"""
        progression_id = str(uuid.uuid4())

        return {
            "status": "chord_progression_created",
            "progression_id": progression_id,
            "chords": chords,
            "tempo": tempo,
            "time_signature": time_signature,
            "chords_per_bar": chords_per_bar,
            "instrument": instrument,
            "description": description,
        }
