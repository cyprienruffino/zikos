"""Tests for tool providers"""

import pytest

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_providers.qwen_tool_provider import QwenToolProvider
from zikos.services.tool_providers.simplified_tool_provider import SimplifiedToolProvider
from zikos.services.tool_providers.structured_tool_provider import StructuredToolProvider


class TestStructuredToolProvider:
    """Tests for StructuredToolProvider"""

    @pytest.fixture
    def provider(self):
        """Create StructuredToolProvider instance"""
        return StructuredToolProvider()

    def test_format_tool_instructions(self, provider):
        """Test formatting tool instructions"""
        instructions = provider.format_tool_instructions()

        assert "TOOL DETAILS" in instructions
        assert "get_tool_definition" in instructions

    def test_format_tool_schemas(self, provider):
        """Test formatting tool schemas"""
        tools = [
            Tool(
                name="test_tool",
                description="A test tool",
                category=ToolCategory.MIDI,
                schema={
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": {"type": "object", "properties": {}, "required": []},
                    },
                },
            )
        ]

        schemas = provider.format_tool_schemas(tools)

        assert "Available Tools" in schemas
        assert "test_tool" in schemas
        assert "function calling format" in schemas

    def test_format_tool_schemas_empty_list(self, provider):
        """Test formatting tool schemas with empty list"""
        schemas = provider.format_tool_schemas([])

        assert "Available Tools" in schemas
        assert "[]" in schemas or "no tools" in schemas.lower()

    def test_get_tool_call_examples(self, provider):
        """Test getting tool call examples"""
        examples = provider.get_tool_call_examples()

        assert "Examples" in examples
        assert "request_audio_recording" in examples
        assert "create_metronome" in examples

    def test_should_inject_tools_as_text(self, provider):
        """Test should_inject_tools_as_text returns False"""
        assert provider.should_inject_tools_as_text() is False

    def test_should_pass_tools_as_parameter(self, provider):
        """Test should_pass_tools_as_parameter returns True"""
        assert provider.should_pass_tools_as_parameter() is True


class TestSimplifiedToolProvider:
    """Tests for SimplifiedToolProvider"""

    @pytest.fixture
    def provider(self):
        """Create SimplifiedToolProvider instance"""
        return SimplifiedToolProvider()

    def test_format_tool_instructions(self, provider):
        """Test formatting tool instructions"""
        instructions = provider.format_tool_instructions()

        assert "TOOL FORMAT" in instructions
        assert "<tool" in instructions

    def test_format_tool_schemas(self, provider):
        """Test formatting tool schemas"""
        tools = [
            Tool(
                name="test_tool",
                description="A test tool",
                category=ToolCategory.MIDI,
                schema={
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": {"type": "object", "properties": {}, "required": []},
                    },
                },
            )
        ]

        schemas = provider.format_tool_schemas(tools)

        assert len(schemas) > 0

    def test_should_inject_tools_as_text(self, provider):
        """Test should_inject_tools_as_text returns True"""
        assert provider.should_inject_tools_as_text() is True

    def test_should_pass_tools_as_parameter(self, provider):
        """Test should_pass_tools_as_parameter returns False"""
        assert provider.should_pass_tools_as_parameter() is False

    def test_summary_is_compact_not_schema_duplicate(self, provider):
        """generate_tool_summary must be a compact category summary — not a
        second copy of format_tool_schemas (which caused double injection)."""
        tools = [
            Tool(
                name="test_tool",
                description="A test tool with a fairly long description",
                category=ToolCategory.MIDI,
                schema={"type": "function", "function": {"name": "test_tool"}},
            ),
            Tool(
                name="other_tool",
                description="Another tool description",
                category=ToolCategory.AUDIO_ANALYSIS,
                schema={"type": "function", "function": {"name": "other_tool"}},
            ),
        ]

        summary = provider.generate_tool_summary(tools)
        schemas = provider.format_tool_schemas(tools)

        assert summary != schemas
        assert "test_tool" in summary
        assert "other_tool" in summary
        # Names only — descriptions live in the schemas section
        assert "A test tool with a fairly long description" not in summary
        assert "A test tool with a fairly long description" in schemas


class TestQwenToolProvider:
    """Tests for QwenToolProvider"""

    @pytest.fixture
    def provider(self):
        """Create QwenToolProvider instance"""
        return QwenToolProvider()

    def test_format_tool_instructions(self, provider):
        """Test formatting tool instructions"""
        instructions = provider.format_tool_instructions()

        assert "TOOL RULES" in instructions
        assert "<tool_call>" in instructions

    def test_get_tool_call_examples(self, provider):
        """Test getting tool call examples"""
        examples = provider.get_tool_call_examples()

        assert "<tool_call>" in examples
        assert "request_audio_recording" in examples

    def test_should_inject_tools_as_text(self, provider):
        """Test should_inject_tools_as_text returns False (tools passed as parameter)"""
        assert provider.should_inject_tools_as_text() is False

    def test_should_pass_tools_as_parameter(self, provider):
        """Test should_pass_tools_as_parameter returns True"""
        assert provider.should_pass_tools_as_parameter() is True
