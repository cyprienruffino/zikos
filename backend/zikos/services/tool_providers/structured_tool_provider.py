"""Structured tool provider implementation"""

import json
from typing import Any

from zikos.mcp.tool import Tool
from zikos.services.tool_provider import ToolProvider


class StructuredToolProvider(ToolProvider):
    """Tool provider for models with native structured function calling (e.g., OpenAI, Claude)"""

    def format_tool_instructions(self) -> str:
        """Structured function calling instructions"""
        return """**CRITICAL**: Call tools directly - NEVER describe them or tell users to use them.

**Practice requests**: User wants to practice/improve something → IMMEDIATELY call `request_audio_recording`. Don't explain - just call it.

**FORBIDDEN**: "You can use tools like..." or "Use tools such as..." - just call the tools directly.

**TOOL DETAILS**: Call `get_tool_definition` with tool name for full details."""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools for structured function calling models"""
        tool_schemas = [tool.to_schema_dict() for tool in tools]
        tools_json = json.dumps(tool_schemas, indent=2)
        return f"""# Available Tools

You have access to the following tools:
{tools_json}

Use these tools by calling them directly - your model handles the function calling format automatically."""

    def get_tool_call_examples(self) -> str:
        """Examples for structured function calling models"""
        return """**Examples**:
User: "I want to practice rhythm" → Call `request_audio_recording` immediately
User: "Help me with timing" → Call `request_audio_recording` immediately
User: "metronome 120 BPM" → Call `create_metronome` with bpm=120

**Remember**: For practice requests, call `request_audio_recording` first - don't explain."""

    def should_inject_tools_as_text(self) -> bool:
        """Structured providers typically don't need text injection"""
        return False

    def should_pass_tools_as_parameter(self) -> bool:
        """Structured providers use structured parameter"""
        return True
