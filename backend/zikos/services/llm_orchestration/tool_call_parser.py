"""Tool call parser base class and format-specific implementations"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from zikos.config import settings

_logger = logging.getLogger("zikos.services.llm_orchestration.tool_call_parser")


class ToolCallParser(ABC):
    """Base class for parsing tool calls from LLM responses"""

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
        # First try native format (for models with native function calling)
        raw_tool_calls = message_obj.get("tool_calls", [])
        if isinstance(raw_tool_calls, list) and raw_tool_calls:
            return raw_tool_calls

        # Then try format-specific parsing
        return self._parse_format_specific(raw_content)

    @abstractmethod
    def _parse_format_specific(self, content: str) -> list[dict[str, Any]]:
        """Parse tool calls using format-specific logic"""
        pass

    @abstractmethod
    def strip_tool_call_tags(self, content: str) -> str:
        """Remove tool call tags from content for display"""
        pass

    def detect_failed_tool_calls(self, content: str) -> str | None:
        """Detect tool call attempts that failed to parse.

        Returns an error message if a partial/malformed tool call is detected,
        None otherwise. Called when no tool calls were successfully parsed.
        """
        return None


class QwenToolCallParser(ToolCallParser):
    """Parser for Qwen's native <tool_call> JSON format"""

    def _parse_format_specific(self, content: str) -> list[dict[str, Any]]:
        """Parse Qwen's <tool_call>{"name": ..., "arguments": ...}</tool_call> format"""
        if not content or "<tool_call>" not in content:
            return []

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

            except json.JSONDecodeError:
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
                                _logger.debug(f"Parsed Qwen tool call (after fix): {tool_name}")
                            continue
                    except Exception:
                        pass

                if settings.debug_tool_calls:
                    _logger.warning("Failed to parse Qwen tool call JSON")
                continue
            except Exception as e:
                if settings.debug_tool_calls:
                    _logger.warning(f"Unexpected error parsing Qwen tool call: {e}")
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

    def detect_failed_tool_calls(self, content: str) -> str | None:
        if not content:
            return None
        if "<tool_call>" in content and "</tool_call>" not in content:
            return 'Malformed tool call: missing </tool_call> closing tag. Expected: <tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>'
        if "<tool_call>" in content:
            # Tags present but parsing returned nothing - likely bad JSON
            pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
            for match in re.finditer(pattern, content, re.DOTALL):
                try:
                    json.loads(match.group(1).strip())
                except (json.JSONDecodeError, Exception):
                    return 'Malformed tool call: invalid JSON inside <tool_call> tags. Expected: <tool_call>{"name": "tool_name", "arguments": {...}}</tool_call>'
        return None

    def strip_tool_call_tags(self, content: str) -> str:
        """Remove <tool_call> tags from content"""
        content = re.sub(r"<tool_call>.*?</tool_call>", "", content, flags=re.DOTALL)

        # Also remove bare JSON tool calls
        lines = content.split("\n")
        filtered_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('{"name"') and '"arguments"' in line:
                brace_count = lines[i].count("{") - lines[i].count("}")
                i += 1
                while i < len(lines) and brace_count > 0:
                    brace_count += lines[i].count("{") - lines[i].count("}")
                    i += 1
            else:
                filtered_lines.append(lines[i])
                i += 1

        return "\n".join(filtered_lines).strip()


class SimplifiedToolCallParser(ToolCallParser):
    """Parser for simplified <tool name="...">key: value</tool> format"""

    def _parse_format_specific(self, content: str) -> list[dict[str, Any]]:
        """Parse simplified XML format"""
        if not content or "<tool " not in content:
            return []

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
                        _logger.debug(f"Parsed simplified tool call: {tool_name}")
                        _logger.debug(f"  Arguments: {arguments}")

            except Exception as e:
                if settings.debug_tool_calls:
                    _logger.warning(f"Failed to parse simplified tool call: {e}")
                continue

        return tool_calls

    def _parse_key_value_params(self, params_text: str) -> dict[str, Any]:
        """Parse key: value parameter format"""
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
            key_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", line)

            if key_match and not is_multiline:
                save_current()
                current_key = key_match.group(1)
                value_part = key_match.group(2).strip()

                if value_part == "|":
                    is_multiline = True
                elif value_part:
                    current_value_lines.append(value_part)

            elif is_multiline and current_key:
                if line.strip():
                    if multiline_indent is None:
                        multiline_indent = len(line) - len(line.lstrip())
                    if len(line) >= multiline_indent:
                        current_value_lines.append(line[multiline_indent:])
                    else:
                        current_value_lines.append(line.strip())
                elif current_value_lines:
                    current_value_lines.append("")

            elif current_key and line.strip():
                current_value_lines.append(line.strip())

        save_current()
        return arguments

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        if not value:
            return ""

        try:
            return int(value)
        except ValueError:
            pass

        try:
            return float(value)
        except ValueError:
            pass

        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False

        return value

    def detect_failed_tool_calls(self, content: str) -> str | None:
        if not content:
            return None
        if "<tool " in content and "</tool>" not in content:
            return 'Malformed tool call: missing </tool> closing tag. Expected: <tool name="tool_name">\\nparam: value\\n</tool>'
        if "<tool " in content:
            # Tags present but no name matched
            if not re.search(r'<tool\s+name="([^"]+)">', content):
                return 'Malformed tool call: bad syntax. Expected: <tool name="tool_name">\\nparam: value\\n</tool>'
        return None

    def strip_tool_call_tags(self, content: str) -> str:
        """Remove simplified tool tags from content"""
        return re.sub(r'<tool\s+name="[^"]*">.*?</tool>', "", content, flags=re.DOTALL).strip()


class NativeToolCallParser(ToolCallParser):
    """Parser that only uses native tool_calls from API response"""

    def _parse_format_specific(self, content: str) -> list[dict[str, Any]]:
        """Native parser doesn't parse content - only uses message.tool_calls"""
        return []

    def strip_tool_call_tags(self, content: str) -> str:
        """No tags to strip for native format"""
        return content.strip()


class HybridToolCallParser(ToolCallParser):
    """Parser that tries multiple formats (for backwards compatibility)"""

    def __init__(self):
        self._qwen_parser = QwenToolCallParser()
        self._simplified_parser = SimplifiedToolCallParser()

    def _parse_format_specific(self, content: str) -> list[dict[str, Any]]:
        """Try simplified format first, then Qwen format"""
        if not content:
            return []

        # Try simplified format first
        if "<tool " in content:
            tool_calls = self._simplified_parser._parse_format_specific(content)
            if tool_calls:
                return tool_calls

        # Fall back to Qwen format
        if "<tool_call>" in content:
            return self._qwen_parser._parse_format_specific(content)

        return []

    def detect_failed_tool_calls(self, content: str) -> str | None:
        return self._simplified_parser.detect_failed_tool_calls(
            content
        ) or self._qwen_parser.detect_failed_tool_calls(content)

    def strip_tool_call_tags(self, content: str) -> str:
        """Remove both simplified and Qwen tags"""
        content = self._simplified_parser.strip_tool_call_tags(content)
        content = self._qwen_parser.strip_tool_call_tags(content)
        return content.strip()


def get_tool_call_parser(tool_format: str | None = None) -> ToolCallParser:
    """Factory function to get appropriate parser based on config

    Args:
        tool_format: One of 'auto', 'qwen', 'simplified', 'native'.
                    If None, reads from settings.

    Returns:
        Appropriate ToolCallParser instance
    """
    if tool_format is None:
        tool_format = settings.llm_tool_format

    parsers: dict[str, type[ToolCallParser]] = {
        "qwen": QwenToolCallParser,
        "simplified": SimplifiedToolCallParser,
        "native": NativeToolCallParser,
        "auto": HybridToolCallParser,
    }

    parser_class = parsers.get(tool_format, HybridToolCallParser)
    return parser_class()
