"""Prepare messages for LLM, handling truncation and system prompt injection"""

from typing import Any

import tiktoken

from zikos.constants import LLM
from zikos.utils.token_budget import get_max_tokens_for_preparation


class MessagePreparer:
    """Prepares messages for LLM, ensuring system prompt is included and history is truncated"""

    def prepare(
        self,
        history: list[dict[str, Any]],
        max_tokens: int | None = None,
        for_user: bool = False,
        context_window: int | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare messages for LLM, ensuring system prompt is included

        For models that don't properly handle system messages (like Phi3),
        prepend the system prompt to the first user message and remove the system message.

        Also truncates conversation history if it exceeds max_tokens to prevent context overflow.
        IMPORTANT: Always preserves audio analysis messages even if they're older.

        Args:
            history: Conversation history
            max_tokens: Maximum tokens to include. If None, uses context_window if provided,
                otherwise falls back to LLM.MAX_TOKENS_PREPARE_MESSAGES
            for_user: If True, filters out thinking messages for user display
            context_window: Actual context window size. Used to calculate max_tokens if not provided.
        """
        if max_tokens is None:
            if context_window is not None:
                max_tokens = get_max_tokens_for_preparation(context_window)
            else:
                max_tokens = LLM.MAX_TOKENS_PREPARE_MESSAGES

        if not history:
            return history

        enc = tiktoken.get_encoding("cl100k_base")

        messages = []
        system_prompt = None
        system_prepended = False
        total_tokens = 0

        audio_analysis_messages = []
        other_messages = []
        for msg in history:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
                continue
            if for_user and msg.get("role") == "thinking":
                continue
            content = str(msg.get("content", ""))
            if any(
                marker in content
                for marker in ["[Audio Analysis", "Audio analysis complete", "audio_file_id"]
            ):
                audio_analysis_messages.append(msg)
            else:
                other_messages.append(msg)

        # Calculate system prompt tokens (includes tool schemas if injected)
        system_prompt_tokens = 0
        if system_prompt:
            system_prompt_tokens = len(enc.encode(system_prompt))

        # Calculate available tokens for conversation history
        # Must account for system prompt size and reserve
        if context_window is not None:
            from zikos.utils.token_budget import calculate_reserve_tokens

            reserve = calculate_reserve_tokens(context_window)
            # Available = max_tokens - system_prompt - reserve
            available_tokens = max_tokens - system_prompt_tokens - reserve

            # If system prompt is too large, we have a problem
            if available_tokens <= 0:
                import logging

                _logger = logging.getLogger(__name__)
                _logger.warning(
                    f"System prompt ({system_prompt_tokens} tokens) + reserve ({reserve} tokens) "
                    f"exceeds max_tokens ({max_tokens}). System prompt is too large for context window."
                )
                # Still try to allow some conversation, but very limited
                available_tokens = max(100, max_tokens // 10)
        else:
            available_tokens = max(
                max_tokens - system_prompt_tokens - LLM.TOKENS_RESERVE_AUDIO_ANALYSIS,
                max_tokens // 2,
            )
            if available_tokens <= 0:
                available_tokens = 100

        processed_messages: list[dict[str, Any]] = []
        first_message_added = False
        for msg in reversed(other_messages):
            msg_tokens = len(enc.encode(str(msg.get("content", ""))))
            if total_tokens + msg_tokens > available_tokens and first_message_added:
                break

            processed_messages.insert(0, msg)
            total_tokens += msg_tokens
            first_message_added = True

        for msg in audio_analysis_messages:
            processed_messages.append(msg)

        # Build final messages, ensuring total doesn't exceed max_tokens
        final_total_tokens = system_prompt_tokens
        for msg in processed_messages:
            msg_content = str(msg.get("content", ""))
            msg_tokens = len(enc.encode(msg_content))

            if msg.get("role") == "user" and system_prompt and not system_prepended:
                # Prepend system prompt to first user message
                combined_content = f"{system_prompt}\n\n{msg_content}"
                combined_tokens = len(enc.encode(combined_content))

                # Check if adding this would exceed limit
                if context_window and final_total_tokens + combined_tokens > max_tokens:
                    # System prompt is too large, truncate it or skip this message
                    # For now, still add it but log a warning
                    import logging

                    _logger = logging.getLogger(__name__)
                    _logger.warning(
                        f"System prompt ({system_prompt_tokens} tokens) + message ({msg_tokens} tokens) "
                        f"exceeds available tokens. Total would be {final_total_tokens + combined_tokens}, "
                        f"max is {max_tokens}"
                    )

                messages.append({"role": "user", "content": combined_content})
                final_total_tokens += combined_tokens
                system_prepended = True
            elif msg.get("role") != "system":
                # Check if adding this message would exceed limit
                if context_window and final_total_tokens + msg_tokens > max_tokens:
                    break
                messages.append(msg)
                final_total_tokens += msg_tokens

        if not messages and system_prompt:
            messages.append({"role": "user", "content": system_prompt})
        elif not messages and other_messages:
            first_msg = other_messages[0]
            if system_prompt:
                combined_content = f"{system_prompt}\n\n{first_msg.get('content', '')}"
                messages.append({"role": "user", "content": combined_content})
            else:
                messages.append(first_msg)

        return messages
