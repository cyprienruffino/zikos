"""Base class for prompt sections"""

from abc import ABC, abstractmethod


class PromptSection(ABC):
    """Base class for all prompt sections"""

    @abstractmethod
    def render(self) -> str:
        """Render this section to text

        Returns:
            The text content of this section
        """
        pass

    def should_include(self) -> bool:
        """Whether this section should be included in the prompt

        Returns:
            True if this section should be included, False otherwise
        """
        return True
