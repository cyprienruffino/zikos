"""MCP server"""

from typing import Any

from zikos.mcp.tools import (
    chord_progression as chord_progression_tools,
)
from zikos.mcp.tools import (
    ear_trainer as ear_trainer_tools,
)
from zikos.mcp.tools import (
    metronome as metronome_tools,
)
from zikos.mcp.tools import (
    midi as midi_tools,
)
from zikos.mcp.tools import (
    practice_timer as practice_timer_tools,
)
from zikos.mcp.tools import (
    recording as recording_tools,
)
from zikos.mcp.tools import (
    tempo_trainer as tempo_trainer_tools,
)
from zikos.mcp.tools import (
    tuner as tuner_tools,
)
from zikos.mcp.tools.audio import AudioAnalysisTools


class MCPServer:
    """MCP server for tool management"""

    def __init__(self):
        self.audio_tools = AudioAnalysisTools()
        self.chord_progression_tools = chord_progression_tools.ChordProgressionTools()
        self.ear_trainer_tools = ear_trainer_tools.EarTrainerTools()
        self.midi_tools = midi_tools.MidiTools()
        self.metronome_tools = metronome_tools.MetronomeTools()
        self.practice_timer_tools = practice_timer_tools.PracticeTimerTools()
        self.recording_tools = recording_tools.RecordingTools()
        self.tempo_trainer_tools = tempo_trainer_tools.TempoTrainerTools()
        self.tuner_tools = tuner_tools.TunerTools()

    def get_tools(self) -> list[dict[str, Any]]:
        """Get all available tools as function schemas"""
        tools = []

        tools.extend(self.audio_tools.get_tool_schemas())
        tools.extend(self.chord_progression_tools.get_tool_schemas())
        tools.extend(self.ear_trainer_tools.get_tool_schemas())
        tools.extend(self.midi_tools.get_tool_schemas())
        tools.extend(self.metronome_tools.get_tool_schemas())
        tools.extend(self.practice_timer_tools.get_tool_schemas())
        tools.extend(self.recording_tools.get_tool_schemas())
        tools.extend(self.tempo_trainer_tools.get_tool_schemas())
        tools.extend(self.tuner_tools.get_tool_schemas())

        return tools

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool by name"""
        audio_tool_names = [
            "analyze_tempo",
            "detect_pitch",
            "analyze_rhythm",
            "analyze_dynamics",
            "analyze_articulation",
            "analyze_timbre",
            "detect_key",
            "detect_chords",
        ]
        if tool_name in audio_tool_names:
            result = await self.audio_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name.startswith("midi_"):
            result = await self.midi_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name == "create_metronome":
            result = await self.metronome_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name == "create_chord_progression":
            result = await self.chord_progression_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name == "create_tempo_trainer":
            result = await self.tempo_trainer_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name == "create_ear_trainer":
            result = await self.ear_trainer_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name == "create_practice_timer":
            result = await self.practice_timer_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name == "create_tuner":
            result = await self.tuner_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        elif tool_name.startswith("recording_"):
            result = await self.recording_tools.call_tool(tool_name, **kwargs)
            return dict(result)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
