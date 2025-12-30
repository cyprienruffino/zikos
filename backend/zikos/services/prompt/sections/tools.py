"""Tool instructions section for system prompt"""

from typing import TYPE_CHECKING

from zikos.services.prompt.sections.base import PromptSection

if TYPE_CHECKING:
    from zikos.mcp.tool_registry import ToolRegistry
    from zikos.services.tool_providers import ToolProvider


class ToolInstructionsSection(PromptSection):
    """Tool instructions section (dynamic, injected at runtime)"""

    def __init__(
        self,
        tool_provider: "ToolProvider",
        tools: list,
        tool_schemas: list[dict],
    ):
        """Initialize tool instructions section

        Args:
            tool_provider: Tool provider for formatting
            tools: List of available tools
            tool_schemas: List of tool schemas
        """
        self.tool_provider = tool_provider
        self.tools = tools
        self.tool_schemas = tool_schemas

    def should_include(self) -> bool:
        """Include only if tools are available and should be injected as text"""
        return (
            bool(self.tools)
            and self.tool_provider
            and self.tool_provider.should_inject_tools_as_text()
        )

    def render(self) -> str:
        """Render tool instructions section"""
        if not self.should_include():
            return ""

        tool_instructions = self.tool_provider.format_tool_instructions()
        tool_summary = self.tool_provider.generate_tool_summary(self.tools)
        tool_schemas_text = self.tool_provider.format_tool_schemas(self.tools)
        tool_examples = self.tool_provider.get_tool_call_examples()

        return f"{tool_instructions}\n\n## Available Tools\n\n{tool_summary}\n\n{tool_schemas_text}\n\n{tool_examples}"
