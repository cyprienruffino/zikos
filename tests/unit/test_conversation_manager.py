"""Tests for ConversationManager"""

import pytest

from zikos.services.llm_orchestration.conversation_manager import ConversationManager


class TestConversationManager:
    """Tests for ConversationManager"""

    @pytest.fixture
    def system_prompt_getter(self):
        """Create mock system prompt getter"""
        return lambda: "You are a helpful assistant."

    @pytest.fixture
    def manager(self, system_prompt_getter):
        """Create ConversationManager instance"""
        return ConversationManager(system_prompt_getter)

    def test_get_history_new_session(self, manager):
        """Test getting history for new session"""
        history = manager.get_history("session_123")

        assert len(history) == 1
        assert history[0]["role"] == "system"
        assert "helpful assistant" in history[0]["content"]

    def test_get_history_existing_session(self, manager):
        """Test getting history for existing session"""
        history1 = manager.get_history("session_123")
        history1.append({"role": "user", "content": "Hello"})

        history2 = manager.get_history("session_123")

        assert history1 is history2
        assert len(history2) == 2
        assert history2[1]["role"] == "user"

    def test_get_history_different_sessions(self, manager):
        """Test getting history for different sessions"""
        history1 = manager.get_history("session_123")
        history2 = manager.get_history("session_456")

        assert history1 is not history2
        assert len(history1) == 1
        assert len(history2) == 1

    def test_get_thinking_for_session_no_session(self, manager):
        """Test getting thinking for non-existent session"""
        result = manager.get_thinking_for_session("nonexistent")

        assert result == []

    def test_get_thinking_for_session_no_thinking(self, manager):
        """Test getting thinking when no thinking messages exist"""
        manager.get_history("session_123")
        manager.get_history("session_123").append({"role": "user", "content": "Hello"})

        result = manager.get_thinking_for_session("session_123")

        assert result == []

    def test_get_thinking_for_session_with_thinking(self, manager):
        """Test getting thinking when thinking messages exist"""
        history = manager.get_history("session_123")
        history.append({"role": "user", "content": "Question"})
        history.append({"role": "thinking", "content": "I need to think about this"})
        history.append({"role": "assistant", "content": "Answer"})

        result = manager.get_thinking_for_session("session_123")

        assert len(result) == 1
        assert result[0]["thinking"] == "I need to think about this"
        assert "before" in result[0]["context"]
        assert "after" in result[0]["context"]
        assert result[0]["position"] == 2

    def test_get_thinking_for_session_multiple_thinking(self, manager):
        """Test getting thinking with multiple thinking messages"""
        history = manager.get_history("session_123")
        history.append({"role": "user", "content": "Question 1"})
        history.append({"role": "thinking", "content": "Thinking 1"})
        history.append({"role": "assistant", "content": "Answer 1"})
        history.append({"role": "user", "content": "Question 2"})
        history.append({"role": "thinking", "content": "Thinking 2"})
        history.append({"role": "assistant", "content": "Answer 2"})

        result = manager.get_thinking_for_session("session_123")

        assert len(result) == 2
        assert result[0]["thinking"] == "Thinking 1"
        assert result[1]["thinking"] == "Thinking 2"

    def test_get_thinking_for_session_thinking_at_start(self, manager):
        """Test getting thinking when thinking is at start of history (after system prompt)"""
        history = manager.get_history("session_123")
        history.append({"role": "thinking", "content": "Thinking"})
        history.append({"role": "assistant", "content": "Answer"})

        result = manager.get_thinking_for_session("session_123")

        assert len(result) == 1
        # System prompt is at index 0, thinking at index 1, so there is a "before" (system prompt)
        assert "before" in result[0]["context"]
        assert result[0]["context"]["before"]["role"] == "system"
        assert "after" in result[0]["context"]

    def test_get_thinking_for_session_thinking_at_end(self, manager):
        """Test getting thinking when thinking is at end of history"""
        history = manager.get_history("session_123")
        history.append({"role": "user", "content": "Question"})
        history.append({"role": "thinking", "content": "Thinking"})

        result = manager.get_thinking_for_session("session_123")

        assert len(result) == 1
        assert "before" in result[0]["context"]
        assert "after" not in result[0]["context"]

    def test_get_thinking_for_session_content_preview_truncated(self, manager):
        """Test that content preview is truncated to 200 characters"""
        long_content = "a" * 300
        history = manager.get_history("session_123")
        history.append({"role": "user", "content": long_content})
        history.append({"role": "thinking", "content": "Thinking"})
        history.append({"role": "assistant", "content": "Answer"})

        result = manager.get_thinking_for_session("session_123")

        assert len(result) == 1
        assert len(result[0]["context"]["before"]["content_preview"]) == 200
