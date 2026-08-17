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
        assert messages[0]["role"] == "system"
        assert "helpful assistant" in messages[0]["content"]

    def test_prepare_keeps_system_prompt_separate(self, preparer):
        """Test preparing messages keeps system prompt separate"""
        history = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]

        messages = preparer.prepare(history, max_tokens=1000, for_user=False)

        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert "helpful assistant" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

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

    def test_injected_error_does_not_replace_system_prompt(self, preparer):
        """A later system-role message (e.g. injected error) must never replace
        the real system prompt: the first system message wins."""
        history = [
            {"role": "system", "content": "You are an expert music teacher with tools."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "system", "content": "ERROR: streaming_error: something went wrong"},
            {"role": "user", "content": "Try again"},
        ]

        messages = preparer.prepare(history, max_tokens=1000, for_user=False)

        assert messages[0]["role"] == "system"
        assert "expert music teacher" in messages[0]["content"]
        # The injected error is kept as ordinary context, not as the prompt
        assert any("streaming_error" in str(m.get("content", "")) for m in messages[1:])

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

    def test_order_preserved_when_untruncated(self, preparer):
        """Without truncation pressure, prepare() must return history verbatim:
        no relocation of pinned audio-analysis messages."""
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "[Audio Analysis Results]\nTempo: 120 BPM"},
            {"role": "assistant", "content": "Nice tempo."},
            {"role": "user", "content": "Thanks"},
        ]

        messages = preparer.prepare(history, max_tokens=10000, for_user=False)

        assert messages == history

    def test_system_prompt_always_first(self, preparer):
        """System prompt must be emitted at index 0 even when the surviving
        window would otherwise start with an assistant or tool message."""
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "assistant", "content": "I'll analyze that."},
            {"role": "user", "content": "OK"},
        ]

        messages = preparer.prepare(history, max_tokens=10000, for_user=False)

        assert messages[0] == {"role": "system", "content": "System prompt"}
        assert messages[1]["role"] == "assistant"

    def test_truncation_does_not_split_tool_pairs(self, preparer):
        """Truncation must drop an assistant(tool_calls) message together with
        its tool results — never leave an orphan on either side."""
        tool_calls = [{"id": "call_1", "function": {"name": "analyze_tempo", "arguments": "{}"}}]
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "old " * 300},
            {"role": "assistant", "content": None, "tool_calls": tool_calls},
            {"role": "tool", "name": "analyze_tempo", "content": "x " * 300, "tool_call_id": "call_1"},
            {"role": "user", "content": "recent question"},
        ]

        # Budget small enough that the tool group cannot fully fit
        messages = preparer.prepare(history, max_tokens=100, for_user=False)

        assistant_ids = {
            tc["id"] for m in messages for tc in (m.get("tool_calls") or []) if isinstance(tc, dict)
        }
        result_ids = {m["tool_call_id"] for m in messages if m.get("role") == "tool"}
        assert assistant_ids == result_ids  # no orphans in either direction
        # The newest user message always survives
        assert any(m.get("content") == "recent question" for m in messages)

    def test_truncation_keeps_pinned_in_position(self, preparer):
        """Pinned audio-analysis messages survive truncation at their original
        position relative to surviving messages."""
        history = [{"role": "system", "content": "System prompt"}]
        history.append({"role": "user", "content": "before " * 200})
        history.append({"role": "user", "content": "[Audio Analysis Results]\nTempo: 100 BPM"})
        history.append({"role": "user", "content": "after " * 200})
        history.append({"role": "user", "content": "latest"})

        messages = preparer.prepare(history, max_tokens=120, for_user=False)

        contents = [str(m.get("content", "")) for m in messages]
        audio_idx = next(i for i, c in enumerate(contents) if "[Audio Analysis" in c)
        latest_idx = contents.index("latest")
        assert messages[0]["role"] == "system"
        assert audio_idx < latest_idx
