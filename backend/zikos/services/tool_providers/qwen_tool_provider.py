"""Qwen-specific tool provider implementation"""

import json
from collections import defaultdict

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_provider import ToolProvider


class QwenToolProvider(ToolProvider):
    """Tool provider for Qwen models using their native <tool_call> JSON format

    Qwen's chat template already handles tool formatting when tools are passed
    as a parameter. This provider adds supplementary instructions to reinforce
    tool usage behavior.
    """

    def format_tool_instructions(self) -> str:
        """Qwen tool calling instructions (supplements chat template)"""
        return """TOOL RULES:
- CALL tools directly - never describe them to the user
- Practice requests → call request_audio_recording IMMEDIATELY
- Use <tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>

WRONG: "I can create a metronome for you"
RIGHT: <tool_call>{"name": "create_metronome", "arguments": {"bpm": 120}}</tool_call>"""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools - Qwen chat template handles full schemas, we add a summary"""
        by_category: dict[ToolCategory, list[str]] = defaultdict(list)
        for tool in tools:
            by_category[tool.category].append(tool.name)

        cat_labels = {
            ToolCategory.AUDIO_ANALYSIS: "Analysis",
            ToolCategory.WIDGET: "Widgets",
            ToolCategory.RECORDING: "Recording",
            ToolCategory.MIDI: "MIDI",
            ToolCategory.OTHER: "Other",
        }

        lines = ["# Tool Summary"]
        for category in [
            ToolCategory.RECORDING,
            ToolCategory.WIDGET,
            ToolCategory.AUDIO_ANALYSIS,
            ToolCategory.MIDI,
            ToolCategory.OTHER,
        ]:
            if category in by_category:
                names = sorted(by_category[category])
                lines.append(f"**{cat_labels[category]}**: {', '.join(names)}")

        return "\n".join(lines)

    def get_tool_call_examples(self) -> str:
        """Examples showing Qwen's native format"""
        return """## Examples

User: "I want to practice scales"
<tool_call>{"name": "request_audio_recording", "arguments": {"prompt": "Play a scale"}}</tool_call>

User: "Give me a metronome at 90 BPM"
<tool_call>{"name": "create_metronome", "arguments": {"bpm": 90, "time_signature": "4/4"}}</tool_call>

User: "Help me with my timing"
<tool_call>{"name": "request_audio_recording", "arguments": {"prompt": "Play something so I can check your timing"}}</tool_call>"""

    def should_inject_tools_as_text(self) -> bool:
        """Inject supplementary instructions (chat template handles full schemas)"""
        return True

    def should_pass_tools_as_parameter(self) -> bool:
        """Pass tools as parameter so Qwen's chat template formats them"""
        return True

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        """Generate compact tool summary"""
        return self.format_tool_schemas(tools)
