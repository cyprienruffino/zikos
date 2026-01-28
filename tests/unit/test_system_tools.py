"""Tests for System tools collection"""

import pytest

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.system.system_collection import SystemTools


class MockToolRegistry:
    """Mock tool registry for testing"""

    def __init__(self, tools: dict[str, Tool] | None = None):
        self._tools = tools or {}

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)


@pytest.fixture
def system_tools():
    """Create SystemTools instance without registry"""
    return SystemTools()


@pytest.fixture
def system_tools_with_registry():
    """Create SystemTools instance with mock registry"""
    mock_tool = Tool(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.OTHER,
        detailed_description="Detailed description for testing",
        schema={
            "type": "function",
            "function": {
                "name": "test_tool",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    )
    registry = MockToolRegistry({"test_tool": mock_tool})
    tools = SystemTools(tool_registry=registry)
    return tools


class TestSystemTools:
    """Tests for SystemTools"""

    def test_get_tools(self, system_tools):
        """Test getting tool definitions"""
        tools = system_tools.get_tools()

        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "get_tool_definition"

    def test_set_tool_registry(self, system_tools):
        """Test setting tool registry after initialization"""
        registry = MockToolRegistry()
        system_tools.set_tool_registry(registry)

        assert system_tools._tool_registry is registry

    @pytest.mark.asyncio
    async def test_call_tool_missing_parameter(self, system_tools_with_registry):
        """Test call_tool with missing tool_name parameter"""
        result = await system_tools_with_registry.call_tool("get_tool_definition")

        assert result["error"] is True
        assert result["error_type"] == "MISSING_PARAMETER"

    @pytest.mark.asyncio
    async def test_call_tool_registry_not_available(self, system_tools):
        """Test call_tool when registry is not set"""
        result = await system_tools.call_tool("get_tool_definition", tool_name="some_tool")

        assert result["error"] is True
        assert result["error_type"] == "REGISTRY_NOT_AVAILABLE"

    @pytest.mark.asyncio
    async def test_call_tool_tool_not_found(self, system_tools_with_registry):
        """Test call_tool when tool is not found"""
        result = await system_tools_with_registry.call_tool(
            "get_tool_definition", tool_name="nonexistent_tool"
        )

        assert result["error"] is True
        assert result["error_type"] == "TOOL_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_call_tool_success(self, system_tools_with_registry):
        """Test call_tool returns tool definition successfully"""
        result = await system_tools_with_registry.call_tool(
            "get_tool_definition", tool_name="test_tool"
        )

        assert "error" not in result
        assert result["name"] == "test_tool"
        assert result["description"] == "A test tool"
        assert result["category"] == "other"
        assert "schema" in result
        assert result["detailed_description"] == "Detailed description for testing"

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, system_tools_with_registry):
        """Test call_tool with unknown tool name"""
        result = await system_tools_with_registry.call_tool("unknown_tool")

        assert result["error"] is True
        assert result["error_type"] == "UNKNOWN_TOOL"
