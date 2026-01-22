"""MCP server"""

import json
from typing import Any

from zikos.config import settings
from zikos.mcp.tool_registry import ToolRegistry
from zikos.mcp.tools import (
    AudioAnalysisTools,
    ChordProgressionTools,
    EarTrainerTools,
    MetronomeTools,
    MidiTools,
    PracticeTimerTools,
    RecordingTools,
    SystemTools,
    TempoTrainerTools,
    TunerTools,
)


class MCPServer:
    """MCP server for tool management"""

    def __init__(self):
        self.audio_tools = AudioAnalysisTools()
        self.chord_progression_tools = ChordProgressionTools()
        self.ear_trainer_tools = EarTrainerTools()
        self.midi_tools = MidiTools()
        self.metronome_tools = MetronomeTools()
        self.practice_timer_tools = PracticeTimerTools()
        self.recording_tools = RecordingTools()
        self.tempo_trainer_tools = TempoTrainerTools()
        self.tuner_tools = TunerTools()

        self._registry = ToolRegistry()
        self._registry.register_many(self.audio_tools.get_tools(), self.audio_tools)
        self._registry.register_many(
            self.chord_progression_tools.get_tools(), self.chord_progression_tools
        )
        self._registry.register_many(self.ear_trainer_tools.get_tools(), self.ear_trainer_tools)
        self._registry.register_many(self.midi_tools.get_tools(), self.midi_tools)
        self._registry.register_many(self.metronome_tools.get_tools(), self.metronome_tools)
        self._registry.register_many(
            self.practice_timer_tools.get_tools(), self.practice_timer_tools
        )
        self._registry.register_many(self.recording_tools.get_tools(), self.recording_tools)
        self._registry.register_many(self.tempo_trainer_tools.get_tools(), self.tempo_trainer_tools)
        self._registry.register_many(self.tuner_tools.get_tools(), self.tuner_tools)

        self.system_tools = SystemTools(self._registry)
        self._registry.register_many(self.system_tools.get_tools(), self.system_tools)

    def get_tools(self) -> list[dict[str, Any]]:
        """Get all available tools as function schemas"""
        schemas: list[dict[str, Any]] = self._registry.get_all_schemas()
        return schemas

    def get_tool_registry(self) -> ToolRegistry:
        """Get the tool registry"""
        return self._registry

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool by name - routes to the appropriate ToolCollection"""
        if settings.debug_tool_calls:
            print(f"[MCP TOOL CALL] {tool_name}")
            print(f"  Arguments: {json.dumps(kwargs, indent=2, default=str)}")

        collection = self._registry.get_collection_for_tool(tool_name)
        if collection is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        result = await collection.call_tool(tool_name, **kwargs)
        return dict(result)
