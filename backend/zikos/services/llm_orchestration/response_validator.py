"""Validate LLM responses for safety and quality"""

import logging
from typing import Any

import tiktoken

from zikos.constants import LLM

_logger = logging.getLogger("zikos.services.llm_orchestration.response_validator")


class ResponseValidator:
    """Validates LLM responses for safety, quality, and loop detection"""

    def validate_token_limit(self, messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Check if conversation exceeds token limit

        Args:
            messages: List of message dictionaries

        Returns:
            Error info dict with 'error_type' and 'error_details' if limit exceeded, None otherwise
        """
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            total_tokens = sum(len(enc.encode(str(msg.get("content", "")))) for msg in messages)
            if total_tokens > LLM.MAX_TOKENS_SAFETY_CHECK:
                return {
                    "error_type": "token_limit",
                    "error_details": f"Conversation exceeds token limit ({total_tokens} tokens, max: {LLM.MAX_TOKENS_SAFETY_CHECK})",
                }
        except Exception:
            pass
        return None

    def validate_response_content(self, content: str) -> dict[str, Any] | None:
        """Validate response content for gibberish patterns

        Args:
            content: Raw response content

        Returns:
            Error info dict with 'error_type' and 'error_details' if gibberish detected, None otherwise
        """
        if not content:
            return None

        words = content.split()

        if len(words) > LLM.MAX_WORDS_RESPONSE:
            _logger.warning(f"Model generated unusually long response ({len(words)} words)")
            return {
                "error_type": "response_too_long",
                "error_details": f"Response exceeds maximum word count ({len(words)} words, max: {LLM.MAX_WORDS_RESPONSE})",
            }

        if len(words) > 50:
            unique_ratio = len(set(words)) / len(words) if words else 0
            if unique_ratio < LLM.MIN_UNIQUE_WORD_RATIO:
                _logger.warning(
                    f"Model generated repetitive output (unique ratio: {unique_ratio:.2f})"
                )
                return {
                    "error_type": "repetitive_output",
                    "error_details": f"Response has low unique word ratio ({unique_ratio:.2f}, min: {LLM.MIN_UNIQUE_WORD_RATIO})",
                }

            single_char_count = len([w for w in words if len(w) == 1 or w.isdigit()])
            if single_char_count > len(words) * LLM.MAX_SINGLE_CHAR_RATIO:
                _logger.warning(
                    "Model generated suspicious pattern (too many single chars/numbers)"
                )
                return {
                    "error_type": "invalid_response_pattern",
                    "error_details": f"Response contains too many single characters/numbers ({single_char_count}/{len(words)})",
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
            Error info dict with 'error_type' and 'error_details' if loop detected, None otherwise
        """
        if max_consecutive is None:
            max_consecutive = LLM.MAX_CONSECUTIVE_TOOL_CALLS

        if consecutive_tool_calls > max_consecutive:
            _logger.warning(
                f"Too many consecutive tool calls ({consecutive_tool_calls}). "
                "Breaking loop to prevent infinite recursion."
            )
            return {
                "error_type": "too_many_tool_calls",
                "error_details": f"Exceeded maximum consecutive tool calls ({consecutive_tool_calls}, max: {max_consecutive})",
            }

        if len(recent_tool_calls) >= LLM.REPETITIVE_PATTERN_THRESHOLD:
            if len(set(recent_tool_calls[-LLM.REPETITIVE_PATTERN_THRESHOLD :])) == 1:
                _logger.warning(
                    f"Detected repetitive tool calling pattern ({recent_tool_calls[-LLM.REPETITIVE_PATTERN_THRESHOLD:]}). "
                    "Breaking loop to prevent infinite recursion."
                )
                tool_name = recent_tool_calls[-1]
                return {
                    "error_type": "repetitive_tool_calls",
                    "error_details": f"Detected repetitive pattern calling tool '{tool_name}' {LLM.REPETITIVE_PATTERN_THRESHOLD} times",
                }

        return None
