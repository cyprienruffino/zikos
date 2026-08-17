"""Extract thinking content from LLM responses"""

import re

# Matched pairs only: <think>...</think> or <thinking>...</thinking>.
# Alternation (not an optional group) so mismatched pairs like
# <think>...</thinking> are NOT treated as a pair.
_PAIR_RE = re.compile(r"<thinking>(.*?)</thinking>|<think>(.*?)</think>", re.DOTALL)
_CLOSE_RE = re.compile(r"</think(?:ing)?>")
_ANY_TAG_RE = re.compile(r"</?think(?:ing)?>")


class ThinkingExtractor:
    """Extracts thinking content from <thinking> or <think> tags in LLM responses"""

    @staticmethod
    def extract(content: str | None) -> tuple[str, str]:
        """Extract thinking content from <thinking> tags

        Handles a lone closing </think> with no opener by treating everything
        before it as thinking — llama.cpp's Qwen3 template emits the opening
        <think> as part of the prompt, so responses arrive with only the closer.

        Args:
            content: Raw content from LLM that may contain <thinking> tags

        Returns:
            tuple: (cleaned_content, thinking_content)
        """
        if content is None:
            return "", ""

        thinking_parts: list[str] = []

        def _collect(match: re.Match) -> str:
            part = match.group(1) if match.group(1) is not None else match.group(2)
            thinking_parts.append(part.strip())
            return ""

        cleaned_content = _PAIR_RE.sub(_collect, content)

        # Lone closing tag with no matching opener: everything before it is thinking.
        lone_close = _CLOSE_RE.search(cleaned_content)
        if lone_close:
            before = cleaned_content[: lone_close.start()]
            # Strip stray tags left over from mismatched pairs (e.g. <think>...</thinking>)
            before = _ANY_TAG_RE.sub("", before).strip()
            if before:
                thinking_parts.insert(0, before)
            cleaned_content = cleaned_content[lone_close.end() :]

        cleaned_content = cleaned_content.strip()
        thinking_content = "\n\n".join(thinking_parts) if thinking_parts else ""

        return cleaned_content, thinking_content
