"""Abstract base class for tool providers"""

from abc import ABC, abstractmethod
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory


class ToolProvider(ABC):
    """Base class for tool providers - handles model-specific tool formatting"""

    @abstractmethod
    def format_tool_instructions(self) -> str:
        """Return model-specific instructions on how to call tools"""
        pass

    @abstractmethod
    def format_tool_schemas(self, tools: list[Tool]) -> str:
        """Format tool schemas for injection into prompt"""
        pass

    @abstractmethod
    def get_tool_call_examples(self) -> str:
        """Return examples showing how to call tools in this model's format"""
        pass

    @abstractmethod
    def should_inject_tools_as_text(self) -> bool:
        """Whether tools should be injected as text in system prompt"""
        pass

    @abstractmethod
    def should_pass_tools_as_parameter(self) -> bool:
        """Whether tools should be passed as structured parameter to LLM"""
        pass

    def generate_tool_summary(self, tools: list[Tool]) -> str:
        """Generate a human-readable summary of available tools, categorized by their category"""
        by_category: dict[ToolCategory, list[tuple[str, str]]] = {}
        for tool in tools:
            if tool.category not in by_category:
                by_category[tool.category] = []
            by_category[tool.category].append((tool.name, tool.description))

        category_labels = {
            ToolCategory.AUDIO_ANALYSIS: "**Audio Analysis Tools:**",
            ToolCategory.WIDGET: "**Practice Widgets:**",
            ToolCategory.RECORDING: "**Recording Tools:**",
            ToolCategory.MIDI: "**MIDI Tools:**",
            ToolCategory.OTHER: "**Other Tools:**",
        }

        lines = []
        for category in [
            ToolCategory.AUDIO_ANALYSIS,
            ToolCategory.WIDGET,
            ToolCategory.RECORDING,
            ToolCategory.MIDI,
            ToolCategory.OTHER,
        ]:
            if category in by_category:
                lines.append(category_labels[category])
                for name, desc in sorted(by_category[category]):
                    lines.append(f"- `{name}` - {desc}")
                lines.append("")

        return "\n".join(lines).strip()
