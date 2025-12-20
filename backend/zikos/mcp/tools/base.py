"""Base class for tool collections"""

from abc import ABC, abstractmethod
from typing import Any

from zikos.mcp.tool import Tool


class ToolCollection(ABC):
    """Base class for tool collections that can provide Tool instances"""

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Get Tool instances for this collection"""
        pass

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas in the legacy format (for backward compatibility)"""
        return [tool.to_schema_dict() for tool in self.get_tools()]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool by name - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement call_tool")
