"""Tool representation and categories"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ToolCategory(Enum):
    """Categories for organizing tools"""

    WIDGET = "widget"
    RECORDING = "recording"
    AUDIO_ANALYSIS = "audio_analysis"
    MIDI = "midi"
    OTHER = "other"


@dataclass
class Tool:
    """Represents a single tool with its metadata and schema"""

    name: str
    description: str
    category: ToolCategory
    schema: dict[str, Any]

    def to_schema_dict(self) -> dict[str, Any]:
        """Convert to the standard schema dict format for LLM"""
        return self.schema

    def __str__(self) -> str:
        return f"Tool(name={self.name}, category={self.category.value})"
