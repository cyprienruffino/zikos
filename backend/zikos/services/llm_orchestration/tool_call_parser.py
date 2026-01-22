"""Parse tool calls from LLM responses"""

import json
import logging
import re
from typing import Any

from zikos.config import settings

_logger = logging.getLogger("zikos.services.llm_orchestration.tool_call_parser")


class ToolCallParser:
    """Parses tool calls from LLM responses, handling both native and Qwen XML formats"""

    def parse_tool_calls(
        self, message_obj: dict[str, Any], raw_content: str
    ) -> list[dict[str, Any]]:
        """Parse tool calls from LLM response

        Args:
            message_obj: Message object from LLM response
            raw_content: Raw content before thinking extraction

        Returns:
            List of tool call dictionaries
        """
        tool_calls: list[dict[str, Any]] = []
        raw_tool_calls = message_obj.get("tool_calls", [])
        if isinstance(raw_tool_calls, list):
            tool_calls = raw_tool_calls

        if not tool_calls and raw_content and "<tool_call>" in raw_content:
            tool_calls = self._parse_qwen_tool_calls(raw_content)

        return tool_calls

    def _parse_qwen_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """Parse Qwen2.5's XML-based tool call format

        Qwen2.5 wraps tool calls in <tool_call> tags:
        <tool_call>
        {"name": "tool_name", "arguments": {...}}
        </tool_call>
        """
        tool_calls: list[dict[str, Any]] = []

        pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            try:
                json_str = match.group(1).strip()
                tool_obj = json.loads(json_str)

                tool_name = tool_obj.get("name")
                tool_args = tool_obj.get("arguments", {})

                if tool_name:
                    tool_calls.append(
                        {
                            "id": f"call_qwen_{len(tool_calls)}",
                            "function": {
                                "name": tool_name,
                                "arguments": (
                                    json.dumps(tool_args)
                                    if isinstance(tool_args, dict)
                                    else str(tool_args)
                                ),
                            },
                        }
                    )

                    if settings.debug_tool_calls:
                        _logger.debug(f"Parsed Qwen tool call: {tool_name}")
                        _logger.debug(f"  Arguments: {tool_args}")
            except json.JSONDecodeError as e:
                json_str = match.group(1).strip()
                fixed_json = self._fix_json_string(json_str)

                if fixed_json != json_str:
                    try:
                        tool_obj = json.loads(fixed_json)
                        tool_name = tool_obj.get("name")
                        tool_args = tool_obj.get("arguments", {})

                        if tool_name:
                            tool_calls.append(
                                {
                                    "id": f"call_qwen_{len(tool_calls)}",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": (
                                            json.dumps(tool_args)
                                            if isinstance(tool_args, dict)
                                            else str(tool_args)
                                        ),
                                    },
                                }
                            )

                            if settings.debug_tool_calls:
                                _logger.debug(
                                    f"Parsed Qwen tool call: {tool_name} (after JSON fix)"
                                )
                                _logger.debug(f"  Arguments: {tool_args}")
                            continue
                    except Exception:
                        pass

                if settings.debug_tool_calls:
                    _logger.warning(f"Failed to parse Qwen tool call JSON: {e}")
                    _logger.debug(f"  Content: {match.group(1)[:200]}")
                continue
            except Exception as e:
                if settings.debug_tool_calls:
                    _logger.warning(f"Unexpected error parsing Qwen tool call: {e}")
                continue

        return tool_calls

    def _fix_json_string(self, json_str: str) -> str:
        """Attempt to fix common JSON issues like unescaped newlines in strings

        This handles cases where the model includes multi-line content
        (like MIDI text) directly in JSON strings without proper escaping.
        """
        result = []
        i = 0
        in_string = False
        escape_next = False

        while i < len(json_str):
            char = json_str[i]

            if escape_next:
                result.append(char)
                escape_next = False
            elif char == "\\":
                result.append(char)
                escape_next = True
            elif char == '"' and not escape_next:
                in_string = not in_string
                result.append(char)
            elif in_string and char in ["\n", "\r", "\t"]:
                if char == "\n":
                    result.append("\\n")
                elif char == "\r":
                    result.append("\\r")
                elif char == "\t":
                    result.append("\\t")
            else:
                result.append(char)

            i += 1

        return "".join(result)

    def strip_tool_call_tags(self, content: str) -> str:
        """Remove <tool_call> XML tags and bare JSON tool calls from content for display"""
        # Remove XML-wrapped tool calls: <tool_call>...</tool_call>
        pattern = r"<tool_call>.*?</tool_call>"
        content = re.sub(pattern, "", content, flags=re.DOTALL)

        # Remove bare JSON tool calls that match the pattern: {"name": "...", "arguments": {...}}
        # This handles cases where tool call JSON appears without XML tags
        # We need to handle nested JSON in arguments, so we find balanced braces
        lines = content.split("\n")
        filtered_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Check if this line looks like the start of a tool call JSON
            if line.startswith('{"name"') and '"arguments"' in line:
                # Try to collect the full JSON object by counting braces
                json_lines = [lines[i]]
                brace_count = lines[i].count("{") - lines[i].count("}")
                i += 1
                while i < len(lines) and brace_count > 0:
                    json_lines.append(lines[i])
                    brace_count += lines[i].count("{") - lines[i].count("}")
                    i += 1
                json_str = "\n".join(json_lines)
                try:
                    tool_obj = json.loads(json_str)
                    # Only remove if it has "name" and "arguments" keys (tool call pattern)
                    if (
                        isinstance(tool_obj, dict)
                        and "name" in tool_obj
                        and "arguments" in tool_obj
                    ):
                        # This is a tool call, skip it
                        continue
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
                # Not a valid tool call or parsing failed, keep the lines
                filtered_lines.extend(json_lines)
            else:
                filtered_lines.append(lines[i])
                i += 1

        content = "\n".join(filtered_lines)
        return content.strip()
