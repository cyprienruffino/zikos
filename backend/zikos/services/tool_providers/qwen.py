"""Qwen2.5 tool provider implementation"""

import json
from typing import Any

from zikos.mcp.tool import Tool
from zikos.services.tool_provider import ToolProvider


class QwenToolProvider(ToolProvider):
    """Tool provider for Qwen2.5 models (XML-based tool calling)"""

    def format_tool_instructions(self) -> str:
        """Qwen-specific tool calling instructions"""
        return """**HOW TO CALL TOOLS**: When you need to use a tool, include it directly in your response using XML format:
<tool_call>
{"name": "tool_name", "arguments": {"param": "value"}}
</tool_call>

**CRITICAL**:
- DO NOT write text asking users to call tools
- DO NOT describe what you would do - just include the tool call
- The tool call should be part of your response content
- The system will automatically detect and execute tool calls"""

    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tools in Qwen's XML format"""
        tool_schemas = [tool.to_schema_dict() for tool in tools]
        tools_json = json.dumps(tool_schemas, indent=2)
        return f"""# Available Tools

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tools_json}
</tools>

When you need to call a function, include it in your response using this format:
<tool_call>
{{"name": "function_name", "arguments": {{"param": "value"}}}}
</tool_call>

The tool call should be included directly in your response content. The system will automatically detect and execute it."""

    def get_tool_call_examples(self) -> str:
        """Examples showing Qwen tool call format"""
        return """**Tool Call Examples**:

User: "Let's record a sample"
Your response should include:
<tool_call>
{"name": "request_audio_recording", "arguments": {"prompt": "Please play something for me to analyze"}}
</tool_call>

User: "I need a metronome at 120 BPM"
Your response should include:
<tool_call>
{"name": "create_metronome", "arguments": {"bpm": 120, "time_signature": "4/4"}}
</tool_call>

**Remember**: Include the tool call directly in your response - don't describe it or ask permission."""

    def should_inject_tools_as_text(self) -> bool:
        """Qwen needs tools injected as text"""
        return True

    def should_pass_tools_as_parameter(self) -> bool:
        """Qwen also supports structured format, but XML is more reliable"""
        return True
