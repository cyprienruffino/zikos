"""Process LLM streaming responses with thinking budget management"""

import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

_logger = logging.getLogger("zikos.services.llm_orchestration.stream_processor")
_conversation_logger = logging.getLogger("zikos.conversation")


@dataclass
class StreamResult:
    """Result from processing a stream iteration"""

    accumulated_content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    thinking_budget_exceeded: bool = False


class StreamProcessor:
    """Processes LLM stream chunks, handling thinking budget and token yielding.

    This is a self-contained state machine that reads tokens from a backend stream,
    manages thinking budget, and yields token dicts for the UI. The final state
    (accumulated content, tool calls, budget status) is written to a StreamResult.
    """

    async def process(
        self,
        stream: AsyncIterator,
        result: StreamResult,
        *,
        nothink_retry: bool = False,
        max_thinking: int = 0,
        session_id: str = "",
    ):
        """Process stream chunks, yielding token dicts for the UI.

        Populates `result` with accumulated content, tool calls, and
        thinking budget status.

        Args:
            stream: Async iterator of LLM response chunks
            result: Mutable result object to populate
            nothink_retry: If True, strip think tags and skip thinking handling
            max_thinking: Max thinking tokens (0=unlimited)
            session_id: For logging

        Yields:
            Token dicts: {"type": "token", "content": "..."}
        """
        in_thinking = not nothink_retry and max_thinking > 0
        thinking_token_count = 0
        accumulated_content = ""
        accumulated_tool_calls: list[dict[str, Any]] = []
        final_delta: dict[str, Any] = {}
        final_finish_reason = None

        _logger.info(
            f"Thinking budget: {max_thinking} tokens (0=unlimited, nothink={nothink_retry})"
        )

        async for chunk in stream:
            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            finish_reason = choice.get("finish_reason")

            if delta.get("content"):
                token = delta.get("content", "")
                if not isinstance(token, str):
                    _logger.warning(f"Non-string token received: {type(token)} = {token}")
                    continue

                _logger.debug(f"Token received: {repr(token)}")
                accumulated_content += token

                if nothink_retry:
                    stripped = re.sub(r"</?think(?:ing)?>", "", token)
                    if stripped:
                        yield {"type": "token", "content": stripped}
                    continue

                if in_thinking:
                    thinking_token_count += 1
                    if "</think>" in accumulated_content or "</thinking>" in accumulated_content:
                        in_thinking = False
                    elif max_thinking > 0 and thinking_token_count >= max_thinking:
                        _logger.info(
                            f"Thinking budget exceeded ({thinking_token_count} tokens), "
                            "truncating and re-generating with /nothink"
                        )
                        _conversation_logger.info(
                            f"Session: {session_id}\n"
                            f"Thinking budget exceeded "
                            f"({thinking_token_count}/{max_thinking} tokens), "
                            f"re-generating with /nothink\n"
                            f"{'=' * 80}"
                        )
                        result.accumulated_content = accumulated_content
                        result.thinking_budget_exceeded = True
                        return
                    continue
                elif "<think" in token:
                    in_thinking = True
                    continue

                yield {"type": "token", "content": token}

            if delta.get("tool_calls"):
                accumulated_tool_calls.extend(delta.get("tool_calls", []))

            if finish_reason:
                final_delta = delta
                final_finish_reason = finish_reason
                if choice.get("tool_calls"):
                    accumulated_tool_calls.extend(choice.get("tool_calls", []))
                break

        result.accumulated_content = accumulated_content
        result.tool_calls = (
            accumulated_tool_calls
            if accumulated_tool_calls
            else (final_delta.get("tool_calls") if final_finish_reason == "tool_calls" else None)
        )
