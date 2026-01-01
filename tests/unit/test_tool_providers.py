"""Tests for tool providers"""

import pytest

from zikos.mcp.tool import Tool, ToolCategory
from zikos.services.tool_providers.openai import OpenAIToolProvider
from zikos.services.tool_providers.qwen import QwenToolProvider


class TestOpenAIToolProvider:
    """Tests for OpenAIToolProvider"""

    @pytest.fixture
    def provider(self):
        """Create OpenAIToolProvider instance"""
        return OpenAIToolProvider()

    def test_format_tool_instructions(self, provider):
        """Test formatting tool instructions"""
        instructions = provider.format_tool_instructions()

        assert "HOW TO CALL TOOLS" in instructions
        assert "native function calling" in instructions
        assert "automatically" in instructions

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

        assert "Tool Usage Examples" in examples
        assert "request_audio_recording" in examples
        assert "create_metronome" in examples

    def test_should_inject_tools_as_text(self, provider):
        """Test should_inject_tools_as_text returns False"""
        assert provider.should_inject_tools_as_text() is False

    def test_should_pass_tools_as_parameter(self, provider):
        """Test should_pass_tools_as_parameter returns True"""
        assert provider.should_pass_tools_as_parameter() is True


class TestQwenToolProvider:
    """Tests for QwenToolProvider"""

    @pytest.fixture
    def provider(self):
        """Create QwenToolProvider instance"""
        return QwenToolProvider()

    def test_format_tool_instructions(self, provider):
        """Test formatting tool instructions"""
        instructions = provider.format_tool_instructions()

        assert len(instructions) > 0

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
        """Test should_inject_tools_as_text"""
        result = provider.should_inject_tools_as_text()
        assert isinstance(result, bool)

    def test_should_pass_tools_as_parameter(self, provider):
        """Test should_pass_tools_as_parameter"""
        result = provider.should_pass_tools_as_parameter()
        assert isinstance(result, bool)
