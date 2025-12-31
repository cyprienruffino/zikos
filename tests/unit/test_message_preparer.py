"""Tests for MessagePreparer"""

from typing import Any

import pytest

from zikos.services.llm_orchestration.message_preparer import MessagePreparer


class TestMessagePreparer:
    """Tests for MessagePreparer"""

    @pytest.fixture
    def preparer(self):
        """Create MessagePreparer instance"""
        return MessagePreparer()

    def test_prepare_empty_history(self, preparer):
        """Test preparing messages with empty history"""
        history: list[dict[str, Any]] = []

        messages = preparer.prepare(history, max_tokens=1000, for_user=False)

        assert messages == []

    def test_prepare_empty_history_with_system_prompt(self, preparer):
        """Test preparing messages with only system prompt in history"""
        history = [{"role": "system", "content": "You are a helpful assistant."}]

        messages = preparer.prepare(history, max_tokens=1000, for_user=False)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "helpful assistant" in messages[0]["content"]

    def test_prepare_combines_system_prompt_with_first_user_message(self, preparer):
        """Test preparing messages combines system prompt with first user message"""
        history = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]

        messages = preparer.prepare(history, max_tokens=1000, for_user=False)

        assert len(messages) >= 1
        assert messages[0]["role"] == "user"
        assert "helpful assistant" in messages[0]["content"]
        assert "Hello" in messages[0]["content"]

    def test_prepare_no_system_prompt_uses_first_message(self, preparer):
        """Test preparing messages uses first message when no system prompt"""
        history = [{"role": "user", "content": "Hello"}]

        messages = preparer.prepare(history, max_tokens=1000, for_user=False)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_prepare_filters_thinking_for_user(self, preparer):
        """Test preparing messages filters thinking messages when for_user=True"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "thinking", "content": "I need to think"},
            {"role": "assistant", "content": "Response"},
        ]

        messages = preparer.prepare(history, max_tokens=1000, for_user=True)

        thinking_messages = [msg for msg in messages if msg.get("role") == "thinking"]
        assert len(thinking_messages) == 0

    def test_prepare_preserves_audio_analysis_messages(self, preparer):
        """Test preparing messages preserves audio analysis messages"""
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Old message"},
            {"role": "user", "content": "[Audio Analysis Results]\nTempo: 120 BPM"},
            {"role": "user", "content": "Recent message"},
        ]

        messages = preparer.prepare(history, max_tokens=100, for_user=False)

        audio_messages = [
            msg for msg in messages if "[Audio Analysis" in str(msg.get("content", ""))
        ]
        assert len(audio_messages) > 0
