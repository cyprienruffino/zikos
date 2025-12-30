"""Prepare messages for LLM, handling truncation and system prompt injection"""

from typing import Any

import tiktoken

from zikos.constants import LLM


class MessagePreparer:
    """Prepares messages for LLM, ensuring system prompt is included and history is truncated"""

    def prepare(
        self, history: list[dict[str, Any]], max_tokens: int | None = None, for_user: bool = False
    ) -> list[dict[str, Any]]:
        """Prepare messages for LLM, ensuring system prompt is included

        For models that don't properly handle system messages (like Phi3),
        prepend the system prompt to the first user message and remove the system message.

        Also truncates conversation history if it exceeds max_tokens to prevent context overflow.
        IMPORTANT: Always preserves audio analysis messages even if they're older.

        Args:
            history: Conversation history
            max_tokens: Maximum tokens to include
            for_user: If True, filters out thinking messages for user display
        """
        if max_tokens is None:
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

        available_tokens = max(max_tokens - LLM.TOKENS_RESERVE_AUDIO_ANALYSIS, max_tokens // 2)

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

        for msg in processed_messages:
            if msg.get("role") == "user" and system_prompt and not system_prepended:
                combined_content = f"{system_prompt}\n\n{msg['content']}"
                messages.append({"role": "user", "content": combined_content})
                system_prepended = True
            elif msg.get("role") != "system":
                messages.append(msg)

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
