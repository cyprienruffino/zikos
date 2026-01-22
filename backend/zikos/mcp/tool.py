"""Tool representation and categories"""

from dataclasses import dataclass, field
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
    parameters: dict[str, Any] | None = None
    required: list[str] | None = None
    detailed_description: str | None = None
    schema: dict[str, Any] | None = None

    def __post_init__(self):
        """Build schema from parameters if schema not provided"""
        if self.schema is None:
            if self.parameters is None:
                raise ValueError("Either 'schema' or 'parameters' must be provided")

            required = self.required or []
            self.schema = {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": self.parameters,
                        "required": required,
                    },
                },
            }

    def to_schema_dict(self) -> dict[str, Any]:
        """Convert to the standard schema dict format for LLM (uses short description)"""
        if self.schema is None:
            raise ValueError("Schema is None - this should not happen after __post_init__")
        return self.schema

    def __str__(self) -> str:
        return f"Tool(name={self.name}, category={self.category.value})"
