"""Unit tests for context window optimization"""

from unittest.mock import MagicMock, patch

import pytest

from zikos.services.llm import LLMService


@pytest.fixture
def mock_backend():
    """Mock LLM backend"""
    backend = MagicMock()
    backend.is_initialized.return_value = True
    backend.get_context_window.return_value = 4096
    backend.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Test response", "role": "assistant"}}]
    }
    return backend


@pytest.fixture
def llm_service(mock_backend):
    """Create LLMService instance with mocked backend"""
    with patch("zikos.services.llm.create_backend", return_value=mock_backend):
        with patch("zikos.services.llm.settings") as mock_settings:
            mock_settings.llm_model_path = "/path/to/model.gguf"
            service = LLMService()
            service.backend = mock_backend
            return service


class TestContextOptimization:
    """Tests for context window optimization"""

    def test_prepare_messages_respects_context_window(self, llm_service):
        """Test that message preparation respects context window"""
        history = [{"role": "system", "content": "System prompt"}]

        # Create many messages that exceed context window
        for i in range(200):
            history.append({"role": "user", "content": f"Message {i} " * 50})  # Large messages
            history.append({"role": "assistant", "content": f"Response {i} " * 50})

        # Prepare messages with a small context window
        messages = llm_service._prepare_messages(history, max_tokens=1000)

        # Should be truncated to fit within limit
        assert len(messages) < len(history)
        assert len(messages) > 0

    def test_prepare_messages_keeps_recent_messages(self, llm_service):
        """Test that recent messages are prioritized"""
        history = [{"role": "system", "content": "System prompt"}]

        # Add old messages
        for i in range(50):
            history.append({"role": "user", "content": f"Old message {i}"})
            history.append({"role": "assistant", "content": f"Old response {i}"})

        # Add recent messages
        for i in range(10):
            history.append({"role": "user", "content": f"Recent message {i}"})
            history.append({"role": "assistant", "content": f"Recent response {i}"})

        messages = llm_service._prepare_messages(history, max_tokens=500)

        # Recent messages should be included
        message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
        assert "Recent message" in message_contents

    def test_prepare_messages_preserves_audio_analysis_despite_size(self, llm_service):
        """Test that audio analysis is preserved even if it's large"""
        history = [
            {"role": "system", "content": "System prompt"},
            {
                "role": "user",
                "content": "[Audio Analysis Results]\n" + "Large analysis data " * 1000,
            },
            {"role": "user", "content": "Message 1" * 100},
            {"role": "user", "content": "Message 2" * 100},
        ]

        messages = llm_service._prepare_messages(history, max_tokens=1000)

        # Audio analysis should be preserved
        audio_found = any(
            "[Audio Analysis Results]" in str(msg.get("content", "")) for msg in messages
        )
        assert audio_found, "Audio analysis should be preserved even if large"

    def test_prepare_messages_handles_empty_history(self, llm_service):
        """Test that empty history is handled correctly"""
        messages = llm_service._prepare_messages([])

        assert isinstance(messages, list)

    def test_prepare_messages_handles_single_system_message(self, llm_service):
        """Test handling of single system message"""
        history = [{"role": "system", "content": "System prompt"}]

        messages = llm_service._prepare_messages(history)

        assert len(messages) > 0
        # System prompt should be prepended to first user message or included
        assert any("System prompt" in str(msg.get("content", "")) for msg in messages)

    def test_context_window_optimization_with_sliding_window(self, llm_service):
        """Test sliding window optimization"""
        history = [{"role": "system", "content": "System prompt"}]

        # Create conversation that exceeds context
        for i in range(100):
            history.append({"role": "user", "content": f"User message {i} " * 20})
            history.append({"role": "assistant", "content": f"Assistant response {i} " * 20})

        # Prepare with limited context
        messages = llm_service._prepare_messages(history, max_tokens=2000)

        # Should keep most recent messages
        assert len(messages) < len(history)

        # Most recent messages should be present
        message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
        # Should have some recent messages (numbers near 99)
        assert any(f"message {i}" in message_contents for i in range(90, 100))
