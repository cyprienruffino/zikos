"""Tests for ConversationManager"""

import asyncio

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

    def test_lock_returns_same_lock_per_session(self, manager):
        lock1 = manager.lock("s1")
        lock2 = manager.lock("s1")
        lock_other = manager.lock("s2")

        assert lock1 is lock2
        assert lock1 is not lock_other
        assert isinstance(lock1, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_lock_serializes_turns(self, manager):
        """Concurrent turns on the same session must not interleave."""
        events: list[str] = []

        async def turn(name: str):
            async with manager.lock("s1"):
                events.append(f"{name}:start")
                await asyncio.sleep(0.01)
                events.append(f"{name}:end")

        await asyncio.gather(turn("a"), turn("b"))

        assert events in (
            ["a:start", "a:end", "b:start", "b:end"],
            ["b:start", "b:end", "a:start", "a:end"],
        )

    def test_lru_eviction_over_max_sessions(self, system_prompt_getter):
        manager = ConversationManager(system_prompt_getter, max_sessions=3)

        for i in range(3):
            manager.get_history(f"s{i}")
        # Refresh s0 so s1 becomes the oldest
        manager.get_history("s0")
        manager.get_history("s3")  # over the cap → evict s1

        assert len(manager.conversations) == 3
        assert "s1" not in manager.conversations
        assert {"s0", "s2", "s3"} == set(manager.conversations)

    def test_eviction_cleans_all_session_state(self, system_prompt_getter):
        manager = ConversationManager(system_prompt_getter, max_sessions=1)
        manager.get_history("old")
        manager.set_pending_interaction("old", "tc1", "request_audio_recording")
        manager.lock("old")

        manager.get_history("new")

        assert "old" not in manager.conversations
        assert manager.pop_pending_interaction("old") is None
        assert "old" not in manager._locks

    def test_locked_sessions_not_evicted(self, system_prompt_getter):
        """A session mid-generation (lock held) must not be evicted."""

        async def run():
            manager = ConversationManager(system_prompt_getter, max_sessions=1)
            manager.get_history("busy")
            async with manager.lock("busy"):
                manager.get_history("other")
                assert "busy" in manager.conversations

        asyncio.run(run())

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
