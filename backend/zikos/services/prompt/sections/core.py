"""Core system prompt section"""

from pathlib import Path

from zikos.services.prompt.sections.base import PromptSection


class CorePromptSection(PromptSection):
    """Core system prompt loaded from SYSTEM_PROMPT.md"""

    def __init__(self, prompt_file_path: Path | None = None):
        """Initialize core prompt section

        Args:
            prompt_file_path: Path to SYSTEM_PROMPT.md. If None, will try to find it
                relative to this file.
        """
        if prompt_file_path is None:
            prompt_file_path = (
                Path(__file__).parent.parent.parent.parent.parent / "SYSTEM_PROMPT.md"
            )
        self.prompt_file_path = prompt_file_path
        self._cached_content: str | None = None

    def render(self) -> str:
        """Render core prompt from file"""
        if self._cached_content is not None:
            return self._cached_content

        if not self.prompt_file_path.exists():
            print("DEBUG: Using fallback system prompt")
            self._cached_content = "You are an expert music teacher AI assistant."
            return self._cached_content

        with open(self.prompt_file_path, encoding="utf-8") as f:
            content = f.read()
            start = content.find("```")
            end = content.find("```", start + 3)
            if start != -1 and end != -1:
                prompt = content[start + 3 : end].strip()
                print(f"DEBUG: System prompt extracted, length: {len(prompt)} chars")
                self._cached_content = prompt
                return prompt
            else:
                self._cached_content = "You are an expert music teacher AI assistant."
                return self._cached_content
