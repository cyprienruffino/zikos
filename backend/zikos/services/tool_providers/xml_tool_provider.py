"""XML-based tool provider implementation"""

import json
from collections import defaultdict
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_provider import ToolProvider


class XMLToolProvider(ToolProvider):
    """Tool provider for models using XML-based tool calling (e.g., Phi-3, Mistral, Qwen)"""

    def format_tool_instructions(self) -> str:
        """XML-based tool calling instructions"""
        return """
**TOOL CALL FORMAT**: <tool_call>{"name": "tool_name", "arguments": {"param": "value"}}</tool_call>
**TOOL DETAILS**: Tool list shows names/categories only. Call `get_tool_definition` for full details."""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools in XML format with only names and categories (no descriptions/parameters)"""
        tool_list = [{"n": tool.name, "c": tool.category.value} for tool in tools]
        tools_json = json.dumps(tool_list, separators=(",", ":"))
        return f"""<tools>{tools_json}</tools>
Abbr: n=name,c=category

Note: Only tool names and categories are shown. Use `get_tool_definition` to retrieve full details (description, parameters, usage guidelines) for any tool."""

    def get_tool_call_examples(self) -> str:
        """Examples showing XML tool call format"""
        return """**Examples**:
User: "I want to practice rhythm" → <tool_call>{"name": "request_audio_recording", "arguments": {"prompt": "Play something to practice rhythm"}}</tool_call>
User: "metronome 120 BPM" → <tool_call>{"name": "create_metronome", "arguments": {"bpm": 120, "time_signature": "4/4"}}</tool_call>

**Remember**: For practice requests, call `request_audio_recording` first - don't explain."""

    def should_inject_tools_as_text(self) -> bool:
        """XML-based providers need tools injected as text"""
        return True

    def should_pass_tools_as_parameter(self) -> bool:
        """Some models support structured format via chat template, others use XML in text"""
        return True

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        """Generate a compact summary of available tools"""
        by_category: dict[ToolCategory, list[str]] = defaultdict(list)
        for tool in tools:
            by_category[tool.category].append(tool.name)

        cat_labels = {
            ToolCategory.AUDIO_ANALYSIS: "Audio Analysis",
            ToolCategory.WIDGET: "Widgets",
            ToolCategory.RECORDING: "Recording",
            ToolCategory.MIDI: "MIDI",
            ToolCategory.OTHER: "Other",
        }

        lines = ["# Available Tools"]
        lines.append("")
        lines.append(
            "Use `get_tool_definition` to retrieve full details (description, parameters, usage guidelines) for any tool."
        )
        lines.append("")
        for category in [
            ToolCategory.AUDIO_ANALYSIS,
            ToolCategory.WIDGET,
            ToolCategory.RECORDING,
            ToolCategory.MIDI,
            ToolCategory.OTHER,
        ]:
            if category in by_category:
                names = sorted(by_category[category])
                lines.append(f"**{cat_labels[category]}**: {', '.join(names)}")

        return "\n".join(lines)
