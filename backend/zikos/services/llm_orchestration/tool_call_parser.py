"""Parse tool calls from LLM responses"""

import json
import logging
import re
from typing import Any

from zikos.config import settings

_logger = logging.getLogger("zikos.services.llm_orchestration.tool_call_parser")


class ToolCallParser:
    """Parses tool calls from LLM responses, handling native and simplified XML formats"""

    def parse_tool_calls(
        self, message_obj: dict[str, Any], raw_content: str
    ) -> list[dict[str, Any]]:
        """Parse tool calls from LLM response

        Args:
            message_obj: Message object from LLM response (may contain native tool_calls)
            raw_content: Raw content before thinking extraction

        Returns:
            List of tool call dictionaries in OpenAI format
        """
        tool_calls: list[dict[str, Any]] = []

        # First try native format (for models with native function calling)
        raw_tool_calls = message_obj.get("tool_calls", [])
        if isinstance(raw_tool_calls, list) and raw_tool_calls:
            tool_calls = raw_tool_calls

        # Then try simplified XML format: <tool name="...">params</tool>
        if not tool_calls and raw_content and "<tool " in raw_content:
            tool_calls = self._parse_simplified_tool_calls(raw_content)

        # Legacy: try old JSON-in-XML format for backwards compatibility
        if not tool_calls and raw_content and "<tool_call>" in raw_content:
            tool_calls = self._parse_legacy_tool_calls(raw_content)

        return tool_calls

    def _parse_simplified_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """Parse simplified XML tool call format

        Format:
            <tool name="tool_name">
            param1: value1
            param2: value2
            </tool>

        For multi-line values (like MIDI):
            <tool name="validate_midi">
            midi_text: |
              MThd...
              MTrk...
            </tool>
        """
        tool_calls: list[dict[str, Any]] = []

        pattern = r'<tool\s+name="([^"]+)">\s*(.*?)\s*</tool>'
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            try:
                tool_name = match.group(1).strip()
                params_text = match.group(2).strip()

                arguments = self._parse_key_value_params(params_text)

                if tool_name:
                    tool_calls.append(
                        {
                            "id": f"call_{len(tool_calls)}",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    )

                    if settings.debug_tool_calls:
                        _logger.debug(f"Parsed tool call: {tool_name}")
                        _logger.debug(f"  Arguments: {arguments}")

            except Exception as e:
                if settings.debug_tool_calls:
                    _logger.warning(f"Failed to parse tool call: {e}")
                    _logger.debug(f"  Content: {match.group(0)[:200]}")
                continue

        return tool_calls

    def _parse_key_value_params(self, params_text: str) -> dict[str, Any]:
        """Parse key: value parameter format

        Handles:
        - Simple values: param: value
        - Multi-line values: param: |
            line1
            line2
        - Numeric values: bpm: 120
        - Boolean-like values: enabled: true
        """
        arguments: dict[str, Any] = {}

        if not params_text:
            return arguments

        lines = params_text.split("\n")
        current_key: str | None = None
        current_value_lines: list[str] = []
        is_multiline = False
        multiline_indent: int | None = None

        def save_current():
            nonlocal current_key, current_value_lines, is_multiline, multiline_indent
            if current_key:
                if is_multiline:
                    value = "\n".join(current_value_lines)
                else:
                    value = " ".join(current_value_lines).strip()
                arguments[current_key] = self._convert_value(value)
            current_key = None
            current_value_lines = []
            is_multiline = False
            multiline_indent = None

        for line in lines:
            # Check for new key: value pair
            key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", line)

            if key_match and not is_multiline:
                save_current()
                current_key = key_match.group(1)
                value_part = key_match.group(2).strip()

                if value_part == "|":
                    # Multi-line value starts
                    is_multiline = True
                elif value_part:
                    current_value_lines.append(value_part)

            elif is_multiline and current_key:
                # Continuation of multi-line value
                if line.strip():
                    # Detect indentation from first non-empty line
                    if multiline_indent is None:
                        multiline_indent = len(line) - len(line.lstrip())
                    # Remove the base indentation
                    if len(line) >= multiline_indent:
                        current_value_lines.append(line[multiline_indent:])
                    else:
                        current_value_lines.append(line.strip())
                elif current_value_lines:
                    # Empty line in multiline - preserve it
                    current_value_lines.append("")

            elif current_key and line.strip():
                # Continuation of single-line value (shouldn't happen often)
                current_value_lines.append(line.strip())

        save_current()
        return arguments

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        if not value:
            return ""

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Boolean-like
        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False

        return value

    def _parse_legacy_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """Parse legacy JSON-in-XML format for backwards compatibility

        Format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
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
                            "id": f"call_legacy_{len(tool_calls)}",
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
                        _logger.debug(f"Parsed legacy tool call: {tool_name}")

            except json.JSONDecodeError as e:
                # Try to fix common JSON issues
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
                                    "id": f"call_legacy_{len(tool_calls)}",
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
                            continue
                    except Exception:
                        pass

                if settings.debug_tool_calls:
                    _logger.warning(f"Failed to parse legacy tool call JSON: {e}")
                continue

        return tool_calls

    def _fix_json_string(self, json_str: str) -> str:
        """Attempt to fix common JSON issues like unescaped newlines"""
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
        """Remove tool call tags from content for display"""
        # Remove simplified format: <tool name="...">...</tool>
        content = re.sub(r'<tool\s+name="[^"]*">.*?</tool>', "", content, flags=re.DOTALL)

        # Remove legacy format: <tool_call>...</tool_call>
        content = re.sub(r"<tool_call>.*?</tool_call>", "", content, flags=re.DOTALL)

        # Remove bare JSON tool calls (legacy)
        lines = content.split("\n")
        filtered_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('{"name"') and '"arguments"' in line:
                # Skip JSON tool call block
                brace_count = lines[i].count("{") - lines[i].count("}")
                i += 1
                while i < len(lines) and brace_count > 0:
                    brace_count += lines[i].count("{") - lines[i].count("}")
                    i += 1
            else:
                filtered_lines.append(lines[i])
                i += 1

        return "\n".join(filtered_lines).strip()
