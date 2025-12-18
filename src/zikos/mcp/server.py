"""MCP server"""

from typing import Any

from src.zikos.mcp.tools import (
    midi as midi_tools,
)
from src.zikos.mcp.tools import (
    recording as recording_tools,
)
from src.zikos.mcp.tools.audio import AudioAnalysisTools


class MCPServer:
    """MCP server for tool management"""

    def __init__(self):
        self.audio_tools = AudioAnalysisTools()
        self.midi_tools = midi_tools.MidiTools()
        self.recording_tools = recording_tools.RecordingTools()

    def get_tools(self) -> list[dict[str, Any]]:
        """Get all available tools as function schemas"""
        tools = []

        tools.extend(self.audio_tools.get_tool_schemas())
        tools.extend(self.midi_tools.get_tool_schemas())
        tools.extend(self.recording_tools.get_tool_schemas())

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
            return await self.audio_tools.call_tool(tool_name, **kwargs)
        elif tool_name.startswith("midi_"):
            return await self.midi_tools.call_tool(tool_name, **kwargs)
        elif tool_name.startswith("recording_"):
            return await self.recording_tools.call_tool(tool_name, **kwargs)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
