"""Tool registry for collecting and organizing tools"""

from collections import defaultdict
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class ToolRegistry:
    """Registry that collects and organizes tools by category"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._by_category: dict[ToolCategory, list[Tool]] = defaultdict(list)
        self._tool_to_collection: dict[str, ToolCollection] = {}

    def register(self, tool: Tool, collection: ToolCollection) -> None:
        """Register a tool with its collection"""
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} is already registered")
        self._tools[tool.name] = tool
        self._by_category[tool.category].append(tool)
        self._tool_to_collection[tool.name] = collection

    def register_many(self, tools: list[Tool], collection: ToolCollection) -> None:
        """Register multiple tools from the same collection"""
        for tool in tools:
            self.register(tool, collection)

    def get_collection_for_tool(self, tool_name: str) -> ToolCollection | None:
        """Get the ToolCollection that handles a specific tool"""
        return self._tool_to_collection.get(tool_name)

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name"""
        return self._tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> list[Tool]:
        """Get all tools in a category"""
        return self._by_category[category].copy()

    def get_all_tools(self) -> list[Tool]:
        """Get all registered tools"""
        return list(self._tools.values())

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Get all tool schemas in the standard format"""
        return [tool.to_schema_dict() for tool in self._tools.values()]

    def get_summary_by_category(self) -> dict[ToolCategory, list[tuple[str, str]]]:
        """Get a summary of tools grouped by category: (name, description)"""
        summary: dict[ToolCategory, list[tuple[str, str]]] = defaultdict(list)
        for tool in self._tools.values():
            summary[tool.category].append((tool.name, tool.description))
        return dict(summary)
