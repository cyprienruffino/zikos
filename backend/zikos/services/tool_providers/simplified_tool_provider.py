"""Simplified tool provider for models that struggle with JSON"""

from collections import defaultdict

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_provider import ToolProvider


class SimplifiedToolProvider(ToolProvider):
    """Tool provider using simplified key:value format for smaller models

    Uses <tool name="...">key: value</tool> format which is easier for
    models that struggle with JSON escaping and bracket matching.

    Tools are listed as name + description only. The model should call
    get_tool_definition before using an unfamiliar tool.
    """

    def format_tool_instructions(self) -> str:
        """Simplified tool calling instructions"""
        return """TOOL FORMAT:
<tool name="tool_name">
param: value
</tool>

For multi-line values (like MIDI):
<tool name="validate_midi">
midi_text: |
  MFile 1 1 480
  MTrk...
</tool>"""

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

        lines = ["# TOOLS"]
        for category in [
            ToolCategory.RECORDING,
            ToolCategory.WIDGET,
            ToolCategory.AUDIO_ANALYSIS,
            ToolCategory.MIDI,
            ToolCategory.OTHER,
        ]:
            if category in by_category:
                lines.append(f"\n**{cat_labels[category]}**")
                for tool in sorted(by_category[category], key=lambda t: t.name):
                    lines.append(f"- {tool.name}: {tool.description}")

        lines.append("\nCall get_tool_definition(tool_name) before using an unfamiliar tool.")
        return "\n".join(lines)

    def get_tool_call_examples(self) -> str:
        """Examples showing simplified tool call format"""
        return """## Examples

User: "I want to practice scales"
<thinking>User wants to practice. I need to request a recording first.</thinking>
<tool name="request_audio_recording">
prompt: Play a scale of your choice, any tempo
</tool>

User: "Give me a metronome at 90 BPM"
<tool name="create_metronome">
bpm: 90
time_signature: 4/4
</tool>"""

    def should_inject_tools_as_text(self) -> bool:
        return True

    def should_pass_tools_as_parameter(self) -> bool:
        return False

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        return self.format_tool_schemas(tools)
