"""Execute tools and handle errors"""

import json
import logging
from typing import Any

from zikos.config import settings
from zikos.mcp.server import MCPServer
from zikos.mcp.tool import ToolCategory
from zikos.mcp.tool_registry import ToolRegistry

_logger = logging.getLogger("zikos.services.llm_orchestration.tool_executor")
_conversation_logger = logging.getLogger("zikos.conversation")


def parse_tool_arguments(tool_call: Any) -> tuple[dict[str, Any], str | None]:
    """Parse a tool call's arguments.

    Single source of truth for argument parsing — malformed arguments are
    reported instead of silently degraded to {}.

    Returns:
        (arguments, error): arguments is {} when parsing fails, and error is a
        human-readable description of what was wrong (None on success).
    """
    if not isinstance(tool_call, dict) or "function" not in tool_call:
        return {}, "Malformed tool call: missing 'function' field"

    tool_args_raw = tool_call["function"].get("arguments", "{}")
    if isinstance(tool_args_raw, dict):
        return tool_args_raw, None
    if not isinstance(tool_args_raw, str):
        return (
            {},
            f"Malformed tool arguments: expected JSON string, got {type(tool_args_raw).__name__}",
        )

    try:
        parsed = json.loads(tool_args_raw or "{}")
    except json.JSONDecodeError as e:
        return {}, f"Malformed tool arguments: invalid JSON ({e})"

    if not isinstance(parsed, dict):
        return {}, f"Malformed tool arguments: expected a JSON object, got {type(parsed).__name__}"
    return parsed, None


class ToolExecutor:
    """Executes tools and handles errors, including widget detection"""

    async def execute_tool_call(
        self,
        tool_call: dict[str, Any],
        tool_registry: ToolRegistry,
        mcp_server: MCPServer,
        session_id: str,
        cleaned_content: str,
        tool_call_parser,
    ) -> dict[str, Any] | None:
        """Execute a single tool call

        Args:
            tool_call: Tool call dictionary from LLM
            tool_registry: Tool registry instance
            mcp_server: MCP server instance
            session_id: Session ID for logging
            cleaned_content: Cleaned content (for widget messages)
            tool_call_parser: ToolCallParser instance for stripping tags

        Returns:
            Widget response dict if widget tool, None otherwise
        """
        if not isinstance(tool_call, dict) or "function" not in tool_call:
            _logger.warning(f"Unexpected tool_call format: {tool_call}")
            return None

        tool_name = tool_call["function"]["name"]
        tool_args, args_error = parse_tool_arguments(tool_call)
        if args_error:
            _logger.warning(f"Failed to parse tool arguments for {tool_name}: {args_error}")

        if settings.debug_tool_calls:
            _logger.debug(f"Tool call: {tool_name}")
            _logger.debug(f"  Tool ID: {tool_call.get('id', 'N/A')}")
            _logger.debug(f"  Arguments: {json.dumps(tool_args, indent=2)}")

        tool = tool_registry.get_tool(tool_name)
        is_widget = tool and tool.category in (
            ToolCategory.DISPLAY_WIDGET,
            ToolCategory.INTERACTION_REQUEST,
        )

        if is_widget:
            if settings.debug_tool_calls:
                print(f"[WIDGET TOOL CALL] {tool_name}")
                _logger.debug(
                    f"Widget tool: Returning {tool_name} to frontend (pausing conversation)"
                )
            widget_content = (
                tool_call_parser.strip_tool_call_tags(cleaned_content) if cleaned_content else ""
            )

            _conversation_logger.info(
                f"Session: {session_id}\n"
                f"Tool Call (Widget): {tool_name}\n"
                f"Arguments: {json.dumps(tool_args, indent=2, default=str)}\n"
                f"Message: {widget_content}\n"
                f"{'=' * 80}"
            )
            return {
                "type": "tool_call",
                "message": widget_content,
                "tool_name": tool_name,
                "tool_id": tool_call.get("id"),
                "arguments": tool_args,
            }

        return None

    async def execute_tool_and_get_result(
        self,
        tool_call: dict[str, Any],
        tool_registry: ToolRegistry,
        mcp_server: MCPServer,
        session_id: str,
    ) -> dict[str, Any]:
        """Execute a tool and return the result message

        Args:
            tool_call: Tool call dictionary from LLM
            tool_registry: Tool registry instance
            mcp_server: MCP server instance
            session_id: Session ID for logging

        Returns:
            Tool result message dictionary
        """
        if not isinstance(tool_call, dict) or "function" not in tool_call:
            tool_name = "unknown"
            tool_call_id = None
        else:
            tool_name = tool_call["function"]["name"]
            tool_call_id = tool_call.get("id")

        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return {
                "role": "tool",
                "name": tool_name,
                "content": f"Error: Tool '{tool_name}' not found",
                "tool_call_id": tool_call_id,
            }

        tool_args, args_error = parse_tool_arguments(tool_call)
        if args_error:
            # Never execute with silently-degraded {} arguments: surface the
            # parse error to the model so it can correct the call.
            _logger.warning(f"Invalid arguments for tool {tool_name}: {args_error}")
            return {
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(
                    {
                        "error": True,
                        "error_type": "invalid_arguments",
                        "message": f"{args_error}. Fix the arguments and call the tool again.",
                    }
                ),
                "tool_call_id": tool_call_id,
            }

        _conversation_logger.info(
            f"Session: {session_id}\n"
            f"Tool Call: {tool_name}\n"
            f"Arguments: {json.dumps(tool_args, indent=2, default=str)}\n"
            f"{'=' * 80}"
        )

        try:
            result = await mcp_server.call_tool(tool_name, **tool_args)

            if settings.debug_tool_calls:
                _logger.debug(f"Tool result: {tool_name}")
                _logger.debug(f"  Result: {json.dumps(result, indent=2, default=str)}")

            _conversation_logger.info(
                f"Session: {session_id}\n"
                f"Tool Result: {tool_name}\n"
                f"Result: {json.dumps(result, indent=2, default=str)}\n"
                f"{'=' * 80}"
            )

            return {
                "role": "tool",
                "name": tool_name,
                "content": json.dumps(result, default=str),
                "tool_call_id": tool_call_id,
            }
        except FileNotFoundError as e:
            error_msg = str(e)
            enhanced_error = self._enhance_file_not_found_error(tool_name, error_msg)

            _logger.warning(f"Tool {tool_name} file not found: {error_msg}")

            return {
                "role": "tool",
                "name": tool_name,
                "content": enhanced_error,
                "tool_call_id": tool_call_id,
            }
        except Exception as e:
            _logger.exception(f"Tool {tool_name} raised an unexpected error")

            return {
                "role": "tool",
                "name": tool_name,
                "content": f"Error: {str(e)}",
                "tool_call_id": tool_call_id,
            }

    def _parse_tool_args(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        """Parse tool arguments from tool call (lenient: {} on failure)"""
        args, _ = parse_tool_arguments(tool_call)
        return args

    def _enhance_file_not_found_error(self, tool_name: str, error_msg: str) -> str:
        """Enhance FileNotFoundError messages with helpful context"""
        if tool_name in ("midi_to_audio", "midi_to_notation") and "not found" in error_msg.lower():
            return (
                f"Error: {error_msg}\n\n"
                "To fix this: First generate MIDI text in your response, then call 'validate_midi' "
                "with that MIDI text. The validate_midi tool will return a midi_file_id that you "
                "can use with midi_to_audio or midi_to_notation."
            )
        return f"Error: {error_msg}"
