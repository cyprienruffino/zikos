"""OpenAI-compatible tool provider implementation"""

import json
from typing import Any

from zikos.mcp.tool import Tool
from zikos.services.tool_provider import ToolProvider


class OpenAIToolProvider(ToolProvider):
    """Tool provider for OpenAI-compatible models (structured function calling)"""

    def format_tool_instructions(self) -> str:
        """OpenAI-style tool calling instructions"""
        return """**HOW TO CALL TOOLS**: You have native function calling capabilities. When you need to use a tool:
1. Your model will automatically include tool calls in your response
2. You don't need to write special syntax - the system handles it automatically
3. DO NOT describe tools or ask users to call them
4. DO NOT write text explaining what you would do - just use the tool directly

The system will detect and execute tool calls automatically."""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools for OpenAI-style models"""
        tool_schemas = [tool.to_schema_dict() for tool in tools]
        tools_json = json.dumps(tool_schemas, indent=2)
        return f"""# Available Tools

You have access to the following tools:
{tools_json}

Use these tools by calling them directly - your model handles the function calling format automatically."""

    def get_tool_call_examples(self) -> str:
        """Examples for OpenAI-style models"""
        return """**Tool Usage Examples**:

User: "Let's record a sample"
→ Call `request_audio_recording` with appropriate prompt

User: "I need a metronome at 120 BPM"
→ Call `create_metronome` with bpm=120

**Remember**: Your model handles the technical format - just use the tools when needed."""

    def should_inject_tools_as_text(self) -> bool:
        """OpenAI models typically don't need text injection"""
        return False

    def should_pass_tools_as_parameter(self) -> bool:
        """OpenAI models use structured parameter"""
        return True
