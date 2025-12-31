"""Tests for ToolInjector"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zikos.services.llm_orchestration.tool_injector import ToolInjector


class TestToolInjector:
    """Tests for ToolInjector"""

    @pytest.fixture
    def tool_injector(self):
        """Create ToolInjector instance"""
        return ToolInjector()

    @pytest.fixture
    def mock_tool_provider(self):
        """Create mock tool provider"""
        provider = MagicMock()
        provider.should_inject_tools_as_text.return_value = True
        return provider

    @pytest.fixture
    def mock_tools(self):
        """Create mock tools"""
        tool = MagicMock()
        tool.name = "test_tool"
        return [tool]

    @pytest.fixture
    def mock_tool_schemas(self):
        """Create mock tool schemas"""
        return [{"function": {"name": "test_tool", "description": "A test tool"}}]

    def test_inject_if_needed_no_tools(self, tool_injector, mock_tool_provider, mock_tool_schemas):
        """Test injection when no tools available"""
        history = [{"role": "system", "content": "System prompt"}]

        result = tool_injector.inject_if_needed(
            history, mock_tool_provider, [], mock_tool_schemas, lambda: "System prompt"
        )

        assert result is False
        assert "<tools>" not in history[0]["content"]

    def test_inject_if_needed_no_provider(self, tool_injector, mock_tools, mock_tool_schemas):
        """Test injection when no tool provider"""
        history = [{"role": "system", "content": "System prompt"}]

        result = tool_injector.inject_if_needed(
            history, None, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is False

    def test_inject_if_needed_provider_should_not_inject(
        self, tool_injector, mock_tools, mock_tool_schemas
    ):
        """Test injection when provider says not to inject"""
        provider = MagicMock()
        provider.should_inject_tools_as_text.return_value = False
        history = [{"role": "system", "content": "System prompt"}]

        result = tool_injector.inject_if_needed(
            history, provider, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is False

    def test_inject_if_needed_already_has_tools(
        self, tool_injector, mock_tool_provider, mock_tools, mock_tool_schemas
    ):
        """Test injection when system prompt already has tools"""
        history = [{"role": "system", "content": "System prompt\n\n<tools>Tool info</tools>"}]

        result = tool_injector.inject_if_needed(
            history, mock_tool_provider, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is False

    def test_inject_if_needed_already_has_tools_alternative_format(
        self, tool_injector, mock_tool_provider, mock_tools, mock_tool_schemas
    ):
        """Test injection when system prompt has tools in alternative format"""
        history = [{"role": "system", "content": "System prompt\n\n# Available Tools\nTool info"}]

        result = tool_injector.inject_if_needed(
            history, mock_tool_provider, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is False

    @patch("zikos.services.llm_orchestration.tool_injector.ToolInstructionsSection")
    def test_inject_if_needed_injects_into_existing_system(
        self, mock_section_class, tool_injector, mock_tool_provider, mock_tools, mock_tool_schemas
    ):
        """Test injection into existing system message"""
        mock_section = MagicMock()
        mock_section.render.return_value = "Tool instructions"
        mock_section_class.return_value = mock_section

        history = [{"role": "system", "content": "System prompt"}]

        result = tool_injector.inject_if_needed(
            history, mock_tool_provider, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is True
        assert "Tool instructions" in history[0]["content"]
        assert "System prompt" in history[0]["content"]

    @patch("zikos.services.llm_orchestration.tool_injector.ToolInstructionsSection")
    def test_inject_if_needed_creates_system_message(
        self, mock_section_class, tool_injector, mock_tool_provider, mock_tools, mock_tool_schemas
    ):
        """Test injection when no system message exists"""
        mock_section = MagicMock()
        mock_section.render.return_value = "Tool instructions"
        mock_section_class.return_value = mock_section

        history = [{"role": "user", "content": "User message"}]

        result = tool_injector.inject_if_needed(
            history, mock_tool_provider, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is True
        assert len(history) == 2
        assert history[0]["role"] == "system"
        assert "System prompt" in history[0]["content"]
        assert "Tool instructions" in history[0]["content"]

    @patch("zikos.services.llm_orchestration.tool_injector.ToolInstructionsSection")
    def test_inject_if_needed_empty_history(
        self, mock_section_class, tool_injector, mock_tool_provider, mock_tools, mock_tool_schemas
    ):
        """Test injection when history is empty"""
        mock_section = MagicMock()
        mock_section.render.return_value = "Tool instructions"
        mock_section_class.return_value = mock_section

        history: list[dict[str, Any]] = []

        result = tool_injector.inject_if_needed(
            history, mock_tool_provider, mock_tools, mock_tool_schemas, lambda: "System prompt"
        )

        assert result is True
        assert len(history) == 1
        assert history[0]["role"] == "system"
