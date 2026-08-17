"""Manage conversation history for LLM sessions"""

import asyncio
import itertools
import logging
from typing import Any

_logger = logging.getLogger("zikos.services.llm_orchestration.conversation_manager")

# Maximum number of concurrently-tracked sessions; oldest by last use is evicted.
MAX_SESSIONS = 100


class ConversationManager:
    """Manages conversation history for different sessions"""

    def __init__(self, system_prompt_getter, max_sessions: int = MAX_SESSIONS):
        self.conversations: dict[str, list[dict[str, Any]]] = {}
        self._get_system_prompt = system_prompt_getter
        self._max_sessions = max_sessions
        # Pending interaction requests: session_id → {tool_call_id, tool_name}
        self._pending_interactions: dict[str, dict[str, str]] = {}
        # Per-session locks serializing generation turns
        self._locks: dict[str, asyncio.Lock] = {}
        # Monotonic last-use counter per session (LRU eviction)
        self._use_counter = itertools.count()
        self._last_used: dict[str, int] = {}

    def lock(self, session_id: str) -> asyncio.Lock:
        """Per-session lock: use as `async with manager.lock(session_id):`."""
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock
        return lock

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for session

        Args:
            session_id: Session identifier

        Returns:
            List of message dictionaries
        """
        if session_id not in self.conversations:
            system_prompt = self._get_system_prompt()
            self.conversations[session_id] = [{"role": "system", "content": system_prompt}]
        self._touch(session_id)
        self._evict_if_needed(current_session=session_id)
        return self.conversations[session_id]

    def _touch(self, session_id: str) -> None:
        self._last_used[session_id] = next(self._use_counter)

    def _evict_if_needed(self, current_session: str) -> None:
        """Evict the least-recently-used sessions beyond the max-session cap."""
        while len(self.conversations) > self._max_sessions:
            candidates = [
                sid
                for sid in self.conversations
                if sid != current_session and not self.lock(sid).locked()
            ]
            if not candidates:
                return
            oldest = min(candidates, key=lambda sid: self._last_used.get(sid, -1))
            self.drop_session(oldest)
            _logger.info(f"Evicted least-recently-used session {oldest} (max={self._max_sessions})")

    def drop_session(self, session_id: str) -> None:
        """Remove all state for a session."""
        self.conversations.pop(session_id, None)
        self._pending_interactions.pop(session_id, None)
        self._locks.pop(session_id, None)
        self._last_used.pop(session_id, None)

    def set_pending_interaction(self, session_id: str, tool_call_id: str, tool_name: str) -> None:
        self._pending_interactions[session_id] = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
        }

    def pop_pending_interaction(self, session_id: str) -> dict[str, str] | None:
        return self._pending_interactions.pop(session_id, None)

    def get_thinking_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all thinking messages for a session (for debugging)

        Returns list of thinking messages with their context (adjacent messages)
        """
        if session_id not in self.conversations:
            return []

        history = self.conversations[session_id]
        thinking_messages = []

        for i, msg in enumerate(history):
            if msg.get("role") == "thinking":
                context = {}
                if i > 0:
                    prev_msg = history[i - 1]
                    context["before"] = {
                        "role": prev_msg.get("role"),
                        "content_preview": str(prev_msg.get("content", ""))[:200],
                    }
                if i < len(history) - 1:
                    next_msg = history[i + 1]
                    context["after"] = {
                        "role": next_msg.get("role"),
                        "content_preview": str(next_msg.get("content", ""))[:200],
                    }

                thinking_messages.append(
                    {
                        "thinking": msg.get("content", ""),
                        "context": context,
                        "position": i,
                    }
                )

        return thinking_messages
