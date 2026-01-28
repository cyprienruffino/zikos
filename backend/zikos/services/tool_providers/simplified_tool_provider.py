"""Simplified tool provider for models that struggle with JSON"""

from collections import defaultdict

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_provider import ToolProvider

# Tools that should have full inline documentation
INLINE_TOOLS = {
    "request_audio_recording",
    "create_metronome",
    "create_tuner",
    "validate_midi",
    "midi_to_audio",
}


class SimplifiedToolProvider(ToolProvider):
    """Tool provider using simplified key:value format for smaller models

    Uses <tool name="...">key: value</tool> format which is easier for
    models that struggle with JSON escaping and bracket matching.
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
</tool>

RULES:
- CALL tools directly - NEVER describe them
- Practice requests → call request_audio_recording IMMEDIATELY
- Think in <thinking> tags, tools go OUTSIDE thinking"""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools with inline docs for common tools"""
        lines = ["# TOOLS\n"]

        inline_docs = []
        other_tools: dict[ToolCategory, list[str]] = defaultdict(list)

        for tool in tools:
            if tool.name in INLINE_TOOLS:
                inline_docs.append(self._format_inline_tool(tool))
            else:
                other_tools[tool.category].append(tool.name)

        if inline_docs:
            lines.append("## Primary Tools\n")
            lines.extend(inline_docs)

        if other_tools:
            lines.append("\n## Other Tools")
            cat_labels = {
                ToolCategory.AUDIO_ANALYSIS: "Analysis",
                ToolCategory.WIDGET: "Widgets",
                ToolCategory.MIDI: "MIDI",
                ToolCategory.OTHER: "Other",
            }
            for category in [
                ToolCategory.AUDIO_ANALYSIS,
                ToolCategory.WIDGET,
                ToolCategory.MIDI,
                ToolCategory.OTHER,
            ]:
                if category in other_tools:
                    names = sorted(other_tools[category])
                    lines.append(f"**{cat_labels[category]}**: {', '.join(names)}")

        return "\n".join(lines)

    def _format_inline_tool(self, tool: Tool) -> str:
        """Format a tool with full inline documentation"""
        params = []
        schema = tool.schema.get("function", {}).get("parameters", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for name, prop in properties.items():
            default = prop.get("default")
            is_required = name in required

            param_str = f"  {name}"
            if not is_required and default is not None:
                param_str += f" (default: {default})"
            elif is_required:
                param_str += " (required)"
            params.append(param_str)

        param_block = "\n".join(params) if params else "  (no parameters)"

        return f"""**{tool.name}**: {tool.description}
Parameters:
{param_block}
"""

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
</tool>

User: "Help me with my intonation"
<thinking>Intonation practice - need to hear them first</thinking>
<tool name="request_audio_recording">
prompt: Play a slow melody so I can check your pitch
</tool>"""

    def should_inject_tools_as_text(self) -> bool:
        """Simplified format requires text injection"""
        return True

    def should_pass_tools_as_parameter(self) -> bool:
        """Don't pass as parameter - we handle everything via text"""
        return False

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        """Generate tool summary"""
        return self.format_tool_schemas(tools)
