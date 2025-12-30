"""Validate LLM responses for safety and quality"""

from typing import Any

import tiktoken

from zikos.constants import LLM


class ResponseValidator:
    """Validates LLM responses for safety, quality, and loop detection"""

    def validate_token_limit(self, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Check if conversation exceeds token limit

        Args:
            messages: List of message dictionaries

        Returns:
            Error response dict if limit exceeded, None otherwise
        """
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            total_tokens = sum(len(enc.encode(str(msg.get("content", "")))) for msg in messages)
            if total_tokens > LLM.MAX_TOKENS_SAFETY_CHECK:
                return {
                    "type": "response",
                    "message": "The conversation is too long. Please start a new conversation or summarize what you need.",
                }
        except Exception:
            pass
        return None

    def validate_response_content(self, content: str) -> dict[str, Any] | None:
        """Validate response content for gibberish patterns

        Args:
            content: Raw response content

        Returns:
            Error response dict if gibberish detected, None otherwise
        """
        if not content:
            return None

        words = content.split()

        if len(words) > LLM.MAX_WORDS_RESPONSE:
            print(f"WARNING: Model generated unusually long response ({len(words)} words)")
            return {
                "type": "response",
                "message": "The model generated an unusually long response. Please try rephrasing your question.",
            }

        if len(words) > 50:
            unique_ratio = len(set(words)) / len(words) if words else 0
            if unique_ratio < LLM.MIN_UNIQUE_WORD_RATIO:
                print(
                    f"WARNING: Model generated repetitive output (unique ratio: {unique_ratio:.2f})"
                )
                return {
                    "type": "response",
                    "message": "The model seems to be repeating itself. Please try rephrasing your question.",
                }

            single_char_count = len([w for w in words if len(w) == 1 or w.isdigit()])
            if single_char_count > len(words) * LLM.MAX_SINGLE_CHAR_RATIO:
                print("WARNING: Model generated suspicious pattern (too many single chars/numbers)")
                return {
                    "type": "response",
                    "message": "The model generated an invalid response. Please try rephrasing your question.",
                }

        return None

    def validate_tool_call_loops(
        self,
        consecutive_tool_calls: int,
        recent_tool_calls: list[str],
        max_consecutive: int | None = None,
    ) -> dict[str, Any] | None:
        """Validate tool call patterns for loops

        Args:
            consecutive_tool_calls: Number of consecutive tool calls
            recent_tool_calls: List of recent tool call names
            max_consecutive: Maximum allowed consecutive tool calls (defaults to constant)

        Returns:
            Error response dict if loop detected, None otherwise
        """
        if max_consecutive is None:
            max_consecutive = LLM.MAX_CONSECUTIVE_TOOL_CALLS

        if consecutive_tool_calls > max_consecutive:
            print(
                f"WARNING: Too many consecutive tool calls ({consecutive_tool_calls}). "
                "Breaking loop to prevent infinite recursion."
            )
            return {
                "type": "response",
                "message": "The model is making too many tool calls. Please try rephrasing your request or breaking it into smaller parts.",
            }

        if len(recent_tool_calls) >= LLM.REPETITIVE_PATTERN_THRESHOLD:
            if len(set(recent_tool_calls[-LLM.REPETITIVE_PATTERN_THRESHOLD :])) == 1:
                print(
                    f"WARNING: Detected repetitive tool calling pattern ({recent_tool_calls[-LLM.REPETITIVE_PATTERN_THRESHOLD:]}). "
                    "Breaking loop to prevent infinite recursion."
                )
                return {
                    "type": "response",
                    "message": "The model appears to be stuck in a loop calling the same tool. Please try rephrasing your request.",
                }

        return None
