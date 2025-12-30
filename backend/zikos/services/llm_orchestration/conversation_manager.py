"""Manage conversation history for LLM sessions"""

from typing import Any


class ConversationManager:
    """Manages conversation history for different sessions"""

    def __init__(self, system_prompt_getter):
        """Initialize conversation manager

        Args:
            system_prompt_getter: Callable that returns the system prompt string
        """
        self.conversations: dict[str, list[dict[str, Any]]] = {}
        self._get_system_prompt = system_prompt_getter

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
        return self.conversations[session_id]

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
