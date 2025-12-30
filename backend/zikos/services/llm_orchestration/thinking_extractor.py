"""Extract thinking content from LLM responses"""

import re


class ThinkingExtractor:
    """Extracts thinking content from <thinking> tags in LLM responses"""

    @staticmethod
    def extract(content: str | None) -> tuple[str, str]:
        """Extract thinking content from <thinking> tags

        Args:
            content: Raw content from LLM that may contain <thinking> tags

        Returns:
            tuple: (cleaned_content, thinking_content)
        """
        if content is None:
            return "", ""

        thinking_parts = []
        pattern = r"<thinking>(.*?)</thinking>"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            thinking_parts.append(match.group(1).strip())

        cleaned_content = re.sub(pattern, "", content, flags=re.DOTALL).strip()

        thinking_content = "\n\n".join(thinking_parts) if thinking_parts else ""

        return cleaned_content, thinking_content
