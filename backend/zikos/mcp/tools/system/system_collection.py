"""System tools collection for metadata and introspection"""

from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class SystemTools(ToolCollection):
    """System tools for tool introspection and metadata"""

    def __init__(self, tool_registry=None):
        """Initialize system tools with access to tool registry"""
        self._tool_registry = tool_registry

    def set_tool_registry(self, tool_registry):
        """Set the tool registry (called after initialization)"""
        self._tool_registry = tool_registry

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="get_tool_definition",
                description="Get the full detailed definition of a tool including interpretation guidelines and usage patterns",
                category=ToolCategory.OTHER,
                detailed_description="""Get the full detailed definition of a tool including interpretation guidelines and usage patterns.

Returns: dict with name, description, category, schema, detailed_description (if available)

Interpretation Guidelines:
- Use this tool to look up detailed information about any tool in the system
- Returns the complete tool definition including parameters, return values, and interpretation guidelines
- detailed_description: Contains interpretation guidelines, usage patterns, and best practices
- Useful when you need to understand how to use a tool correctly or interpret its results
- The schema shows the exact parameter structure and types required
- Use to refresh your understanding of tool capabilities and proper usage
- This is a meta-tool for tool introspection and learning""",
                schema={
                    "type": "function",
                    "function": {
                        "name": "get_tool_definition",
                        "description": "Get the full detailed definition of a tool including interpretation guidelines and usage patterns",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": "Name of the tool to get the definition for",
                                },
                            },
                            "required": ["tool_name"],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool by name"""
        if tool_name == "get_tool_definition":
            tool_name_param = kwargs.get("tool_name")
            if not tool_name_param:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "tool_name is required",
                }

            if not self._tool_registry:
                return {
                    "error": True,
                    "error_type": "REGISTRY_NOT_AVAILABLE",
                    "message": "Tool registry is not available",
                }

            tool = self._tool_registry.get_tool(tool_name_param)
            if not tool:
                return {
                    "error": True,
                    "error_type": "TOOL_NOT_FOUND",
                    "message": f"Tool '{tool_name_param}' not found",
                }

            result = {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "schema": tool.schema,
            }

            if tool.detailed_description:
                result["detailed_description"] = tool.detailed_description

            return result

        return {
            "error": True,
            "error_type": "UNKNOWN_TOOL",
            "message": f"Unknown tool: {tool_name}",
        }
