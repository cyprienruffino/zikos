"""Process LLM streaming responses with thinking budget management"""

import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger("zikos.services.llm_orchestration.stream_processor")
_conversation_logger = logging.getLogger("zikos.conversation")

_OPEN_TAG_RE = re.compile(r"<think(?:ing)?>")
_CLOSE_TAG_RE = re.compile(r"</think(?:ing)?>")
_OPEN_TAGS = ("<thinking>", "<think>")
_CLOSE_TAGS = ("</thinking>", "</think>")

# Rough chars-per-token estimate used to convert the token budget into a
# character budget (thinking is counted on accumulated characters, not chunks).
_CHARS_PER_TOKEN = 4


def _partial_tag_suffix(text: str, tags: tuple[str, ...]) -> int:
    """Length of the longest suffix of text that is a proper prefix of any tag.

    Used to hold back a few characters so tags split across stream chunks are
    still recognized.
    """
    max_len = max(len(t) for t in tags) - 1
    for k in range(min(len(text), max_len), 0, -1):
        suffix = text[-k:]
        if any(tag.startswith(suffix) for tag in tags):
            return k
    return 0


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

        Responses are assumed to be visible text until an actual <think> tag is
        observed — never assumed to start in thinking mode. Chunks are split at
        tag boundaries, and a few characters are buffered so tags split across
        chunks are still recognized.

        Args:
            stream: Async iterator of LLM response chunks
            result: Mutable result object to populate
            nothink_retry: If True, strip think tags and skip thinking handling
            max_thinking: Max thinking tokens (0=unlimited)
            session_id: For logging

        Yields:
            Token dicts: {"type": "token", "content": "..."}
        """
        in_thinking = False
        thinking_chars = 0
        thinking_char_budget = max_thinking * _CHARS_PER_TOKEN
        accumulated_content = ""
        accumulated_tool_calls: list[dict[str, Any]] = []
        pending = ""  # partial-tag buffer carried between chunks

        _logger.info(
            f"Thinking budget: {max_thinking} tokens (0=unlimited, nothink={nothink_retry})"
        )

        async for chunk in stream:
            choices = chunk.get("choices") or []
            if not choices:
                # Some providers emit keep-alive/usage chunks with empty choices
                continue
            choice = choices[0]
            delta = choice.get("delta", {})
            finish_reason = choice.get("finish_reason")

            if delta.get("content"):
                token = delta.get("content", "")
                if not isinstance(token, str):
                    _logger.warning(f"Non-string token received: {type(token)} = {token}")
                    continue

                accumulated_content += token

                if nothink_retry:
                    stripped = re.sub(r"</?think(?:ing)?>", "", token)
                    if stripped:
                        yield {"type": "token", "content": stripped}
                    continue

                buf = pending + token
                pending = ""
                while buf:
                    if in_thinking:
                        match = _CLOSE_TAG_RE.search(buf)
                        if match:
                            thinking_chars += match.start()
                            buf = buf[match.end() :]
                            in_thinking = False
                            continue
                        keep = _partial_tag_suffix(buf, _CLOSE_TAGS)
                        thinking_chars += len(buf) - keep
                        pending = buf[-keep:] if keep else ""
                        buf = ""
                    else:
                        match = _OPEN_TAG_RE.search(buf)
                        if match:
                            if match.start():
                                yield {"type": "token", "content": buf[: match.start()]}
                            buf = buf[match.end() :]
                            in_thinking = True
                            continue
                        keep = _partial_tag_suffix(buf, _OPEN_TAGS)
                        visible = buf[: len(buf) - keep] if keep else buf
                        if visible:
                            yield {"type": "token", "content": visible}
                        pending = buf[-keep:] if keep else ""
                        buf = ""

                if in_thinking and max_thinking > 0 and thinking_chars > thinking_char_budget:
                    _logger.info(
                        f"Thinking budget exceeded ({thinking_chars} chars > "
                        f"{thinking_char_budget}), truncating and re-generating with /nothink"
                    )
                    _conversation_logger.info(
                        f"Session: {session_id}\n"
                        f"Thinking budget exceeded "
                        f"({thinking_chars}/{thinking_char_budget} chars), "
                        f"re-generating with /nothink\n"
                        f"{'=' * 80}"
                    )
                    result.accumulated_content = accumulated_content
                    result.thinking_budget_exceeded = True
                    return

            if delta.get("tool_calls"):
                accumulated_tool_calls.extend(delta.get("tool_calls", []))

            if finish_reason:
                # Only add from choice.tool_calls when delta.tool_calls was not already present
                # in this same chunk — some backends (e.g. CloudBackend) set both, which
                # would double-count the same tool_calls.
                if choice.get("tool_calls") and not delta.get("tool_calls"):
                    accumulated_tool_calls.extend(choice.get("tool_calls", []))
                break

        # Flush any held-back partial-tag characters that never became a tag
        if pending and not in_thinking:
            yield {"type": "token", "content": pending}

        result.accumulated_content = accumulated_content
        result.tool_calls = accumulated_tool_calls or None
