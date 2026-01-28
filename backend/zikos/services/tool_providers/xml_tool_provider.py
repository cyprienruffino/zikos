"""XML-based tool provider implementation"""

from collections import defaultdict

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_provider import ToolProvider

# Tools that should have full inline documentation (most commonly used)
INLINE_TOOLS = {
    "request_audio_recording",
    "create_metronome",
    "create_tuner",
    "validate_midi",
    "midi_to_audio",
}


class XMLToolProvider(ToolProvider):
    """Tool provider for models using simplified XML tool calling"""

    def format_tool_instructions(self) -> str:
        """Simplified XML tool calling instructions"""
        return """TOOL FORMAT:
<tool name="tool_name">
param: value
</tool>

For multi-line values:
<tool name="validate_midi">
midi_text: |
  MThd...
</tool>"""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools - inline common tools, list others by category"""
        lines = ["# TOOLS\n"]

        # Inline documentation for critical tools
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

        # List remaining tools by category
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

User: "Can you show me what that melody sounds like?"
<thinking>I'll write MIDI for the melody and synthesize it.</thinking>
<tool name="validate_midi">
midi_text: |
  MFile 1 1 480
  MTrk
  0 Tempo 500000
  0 KeySig 0 major
  0 PrCh ch=1 p=0
  0 On ch=1 n=60 v=80
  480 Off ch=1 n=60 v=0
  TrkEnd
</tool>
Then after validation succeeds, call midi_to_audio with the midi_file_id."""

    def should_inject_tools_as_text(self) -> bool:
        """XML-based providers need tools injected as text"""
        return True

    def should_pass_tools_as_parameter(self) -> bool:
        """Don't pass tools as parameter - we inject them as text"""
        return False

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        """Generate a compact summary - delegates to format_tool_schemas"""
        return self.format_tool_schemas(tools)
