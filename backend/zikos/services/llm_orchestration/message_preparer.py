"""Prepare messages for LLM, handling truncation and system prompt injection"""

import logging
from typing import Any

import tiktoken

from zikos.constants import LLM
from zikos.utils.token_budget import calculate_reserve_tokens, get_max_tokens_for_preparation

_logger = logging.getLogger(__name__)

_AUDIO_ANALYSIS_MARKERS = ("[Audio Analysis", "Audio analysis complete")


class MessagePreparer:
    """Prepares messages for LLM, ensuring system prompt is included and history is truncated"""

    def prepare(
        self,
        history: list[dict[str, Any]],
        max_tokens: int | None = None,
        for_user: bool = False,
        context_window: int | None = None,
    ) -> list[dict[str, Any]]:
        """Prepare messages for LLM, ensuring system prompt is included.

        Guarantees:
        - The system prompt (FIRST system message in history) is always emitted
          at index 0. Later system-role messages are treated as ordinary context.
        - Message order is preserved exactly; nothing is relocated.
        - Pinned audio-analysis messages are always kept, at their original
          positions (truncation drops messages around them).
        - Truncation never splits an assistant(tool_calls) message from its
          following tool results: the whole group is kept or dropped together.

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

        # Split off the real system prompt (first system message). Later
        # system-role messages (e.g. injected notes) are ordinary context.
        system_prompt: str | None = None
        body: list[dict[str, Any]] = []
        for msg in history:
            if msg.get("role") == "system" and system_prompt is None:
                system_prompt = msg.get("content", "")
                continue
            if for_user and msg.get("role") == "thinking":
                continue
            body.append(msg)

        system_prompt_tokens = len(enc.encode(system_prompt)) if system_prompt else 0

        available_tokens = self._available_tokens(max_tokens, system_prompt_tokens, context_window)

        # Group assistant(tool_calls) messages with their following tool results
        # so truncation can never orphan a tool_use/tool_result pair.
        groups = self._group_messages(body)

        def group_tokens(group: list[dict[str, Any]]) -> int:
            return sum(len(enc.encode(str(m.get("content") or ""))) for m in group)

        def is_pinned(group: list[dict[str, Any]]) -> bool:
            # Only user-role messages are pinned as audio analysis context — never
            # tool results or assistant messages.
            return any(
                m.get("role") == "user"
                and any(marker in str(m.get("content", "")) for marker in _AUDIO_ANALYSIS_MARKERS)
                for m in group
            )

        # Pinned groups are always included; then include groups from newest to
        # oldest until the budget is exhausted. The newest group is always kept.
        included = [False] * len(groups)
        total_tokens = 0
        for idx, group in enumerate(groups):
            if is_pinned(group):
                included[idx] = True
                total_tokens += group_tokens(group)

        newest_added = False
        for idx in range(len(groups) - 1, -1, -1):
            if included[idx]:
                newest_added = True
                continue
            tokens = group_tokens(groups[idx])
            if newest_added and total_tokens + tokens > available_tokens:
                break  # everything older (except pinned) is dropped
            included[idx] = True
            total_tokens += tokens
            newest_added = True

        # Emit in ORIGINAL order, system prompt always first.
        messages: list[dict[str, Any]] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        for idx, group in enumerate(groups):
            if included[idx]:
                messages.extend(group)

        return messages

    def _available_tokens(
        self, max_tokens: int, system_prompt_tokens: int, context_window: int | None
    ) -> int:
        """Compute the token budget available for conversation history."""
        if context_window is not None:
            reserve = int(calculate_reserve_tokens(context_window))
            available_tokens = max_tokens - system_prompt_tokens - reserve

            if available_tokens <= 0:
                _logger.warning(
                    f"System prompt ({system_prompt_tokens} tokens) + reserve ({reserve} tokens) "
                    f"exceeds max_tokens ({max_tokens}). System prompt is too large for context window."
                )
                # Still try to allow some conversation, but very limited
                available_tokens = max(100, max_tokens // 10)
            return available_tokens

        available_tokens = max(
            max_tokens - system_prompt_tokens - LLM.TOKENS_RESERVE_AUDIO_ANALYSIS,
            max_tokens // 2,
        )
        return available_tokens if available_tokens > 0 else 100

    @staticmethod
    def _group_messages(body: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Group each assistant(tool_calls) message with its following tool results."""
        groups: list[list[dict[str, Any]]] = []
        i = 0
        while i < len(body):
            msg = body[i]
            group = [msg]
            i += 1
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                while i < len(body) and body[i].get("role") == "tool":
                    group.append(body[i])
                    i += 1
            groups.append(group)
        return groups
