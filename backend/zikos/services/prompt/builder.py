"""System prompt builder"""

from zikos.services.prompt.sections.base import PromptSection


class SystemPromptBuilder:
    """Builder for assembling system prompts from modular sections"""

    def __init__(self):
        """Initialize builder"""
        self.sections: list[PromptSection] = []

    def add_section(self, section: PromptSection) -> "SystemPromptBuilder":
        """Add a section to the prompt

        Args:
            section: The prompt section to add

        Returns:
            Self for method chaining
        """
        self.sections.append(section)
        return self

    def build(self) -> str:
        """Build the complete system prompt from all sections

        Returns:
            The complete system prompt as a single string
        """
        parts = []
        for section in self.sections:
            if section.should_include():
                rendered = section.render()
                if rendered:
                    parts.append(rendered)

        return "\n\n".join(parts)

    def clear(self) -> "SystemPromptBuilder":
        """Clear all sections

        Returns:
            Self for method chaining
        """
        self.sections.clear()
        return self
