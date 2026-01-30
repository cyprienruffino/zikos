"""Qwen-specific tool provider implementation"""

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
- Practice requests -> call request_audio_recording IMMEDIATELY
- Use <tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>
- Call get_tool_definition before using an unfamiliar tool"""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools as compact name + description list"""
        by_category: dict[ToolCategory, list[Tool]] = defaultdict(list)
        for tool in tools:
            by_category[tool.category].append(tool)

        cat_labels = {
            ToolCategory.RECORDING: "Recording",
            ToolCategory.WIDGET: "Widgets",
            ToolCategory.AUDIO_ANALYSIS: "Analysis",
            ToolCategory.MIDI: "MIDI",
            ToolCategory.OTHER: "Utility",
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
                names = sorted(by_category[category], key=lambda t: t.name)
                tool_list = ", ".join(t.name for t in names)
                lines.append(f"**{cat_labels[category]}**: {tool_list}")

        return "\n".join(lines)

    def get_tool_call_examples(self) -> str:
        """Examples showing Qwen's native format"""
        return """## Examples

User: "I want to practice scales"
<tool_call>{"name": "request_audio_recording", "arguments": {"prompt": "Play a scale"}}</tool_call>

User: "Give me a metronome at 90 BPM"
<tool_call>{"name": "create_metronome", "arguments": {"bpm": 90, "time_signature": "4/4"}}</tool_call>"""

    def should_inject_tools_as_text(self) -> bool:
        return False

    def should_pass_tools_as_parameter(self) -> bool:
        return True

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        return self.format_tool_schemas(tools)
