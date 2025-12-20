"""Tests for tool registry"""

import pytest

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tool_registry import ToolRegistry
from zikos.mcp.tools.base import ToolCollection


class MockToolCollection(ToolCollection):
    """Mock tool collection for testing"""

    def get_tools(self) -> list[Tool]:
        return []

    async def call_tool(self, tool_name: str, **kwargs):
        return {}


@pytest.fixture
def registry():
    """Create ToolRegistry instance"""
    return ToolRegistry()


@pytest.fixture
def sample_tool():
    """Create a sample tool"""
    return Tool(
        name="test_tool",
        description="Test tool description",
        category=ToolCategory.AUDIO_ANALYSIS,
        schema={"type": "function", "function": {"name": "test_tool"}},
    )


@pytest.fixture
def mock_collection():
    """Create a mock tool collection"""
    return MockToolCollection()


class TestToolRegistry:
    """Tests for ToolRegistry"""

    def test_register_tool(self, registry, sample_tool, mock_collection):
        """Test registering a single tool"""
        registry.register(sample_tool, mock_collection)

        assert registry.get_tool("test_tool") == sample_tool
        assert registry.get_collection_for_tool("test_tool") == mock_collection

    def test_register_duplicate_tool(self, registry, sample_tool, mock_collection):
        """Test registering a duplicate tool raises error"""
        registry.register(sample_tool, mock_collection)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_tool, mock_collection)

    def test_register_many(self, registry, mock_collection):
        """Test registering multiple tools"""
        tools = [
            Tool(
                name=f"tool_{i}",
                description=f"Tool {i}",
                category=ToolCategory.AUDIO_ANALYSIS,
                schema={"type": "function", "function": {"name": f"tool_{i}"}},
            )
            for i in range(3)
        ]

        registry.register_many(tools, mock_collection)

        assert len(registry.get_all_tools()) == 3
        for i in range(3):
            assert registry.get_tool(f"tool_{i}") is not None

    def test_get_tool(self, registry, sample_tool, mock_collection):
        """Test getting a tool by name"""
        registry.register(sample_tool, mock_collection)

        assert registry.get_tool("test_tool") == sample_tool
        assert registry.get_tool("nonexistent") is None

    def test_get_tools_by_category(self, registry, mock_collection):
        """Test getting tools by category"""
        audio_tool = Tool(
            name="audio_tool",
            description="Audio tool",
            category=ToolCategory.AUDIO_ANALYSIS,
            schema={"type": "function", "function": {"name": "audio_tool"}},
        )
        midi_tool = Tool(
            name="midi_tool",
            description="MIDI tool",
            category=ToolCategory.MIDI,
            schema={"type": "function", "function": {"name": "midi_tool"}},
        )

        registry.register(audio_tool, mock_collection)
        registry.register(midi_tool, mock_collection)

        audio_tools = registry.get_tools_by_category(ToolCategory.AUDIO_ANALYSIS)
        assert len(audio_tools) == 1
        assert audio_tools[0].name == "audio_tool"

        midi_tools = registry.get_tools_by_category(ToolCategory.MIDI)
        assert len(midi_tools) == 1
        assert midi_tools[0].name == "midi_tool"

    def test_get_all_tools(self, registry, mock_collection):
        """Test getting all tools"""
        tools = [
            Tool(
                name=f"tool_{i}",
                description=f"Tool {i}",
                category=ToolCategory.AUDIO_ANALYSIS,
                schema={"type": "function", "function": {"name": f"tool_{i}"}},
            )
            for i in range(3)
        ]

        registry.register_many(tools, mock_collection)

        all_tools = registry.get_all_tools()
        assert len(all_tools) == 3
        assert all(isinstance(tool, Tool) for tool in all_tools)

    def test_get_all_schemas(self, registry, sample_tool, mock_collection):
        """Test getting all tool schemas"""
        registry.register(sample_tool, mock_collection)

        schemas = registry.get_all_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "test_tool"

    def test_get_summary_by_category(self, registry, mock_collection):
        """Test getting summary by category"""
        audio_tool = Tool(
            name="audio_tool",
            description="Audio tool description",
            category=ToolCategory.AUDIO_ANALYSIS,
            schema={"type": "function", "function": {"name": "audio_tool"}},
        )
        midi_tool = Tool(
            name="midi_tool",
            description="MIDI tool description",
            category=ToolCategory.MIDI,
            schema={"type": "function", "function": {"name": "midi_tool"}},
        )

        registry.register(audio_tool, mock_collection)
        registry.register(midi_tool, mock_collection)

        summary = registry.get_summary_by_category()

        assert ToolCategory.AUDIO_ANALYSIS in summary
        assert ToolCategory.MIDI in summary

        audio_summary = summary[ToolCategory.AUDIO_ANALYSIS]
        assert len(audio_summary) == 1
        assert audio_summary[0] == ("audio_tool", "Audio tool description")

        midi_summary = summary[ToolCategory.MIDI]
        assert len(midi_summary) == 1
        assert midi_summary[0] == ("midi_tool", "MIDI tool description")

    def test_get_collection_for_tool(self, registry, sample_tool, mock_collection):
        """Test getting collection for a tool"""
        registry.register(sample_tool, mock_collection)

        assert registry.get_collection_for_tool("test_tool") == mock_collection
        assert registry.get_collection_for_tool("nonexistent") is None

    def test_tool_str_representation(self, sample_tool):
        """Test Tool string representation"""
        tool_str = str(sample_tool)
        assert "test_tool" in tool_str
        assert "audio_analysis" in tool_str
