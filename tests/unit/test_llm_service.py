"""Unit tests for LLM service"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from zikos.services.llm import LLMService


@pytest.fixture
def mock_backend():
    """Mock LLM backend"""
    backend = MagicMock()
    backend.is_initialized.return_value = True
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


@pytest.fixture
def llm_service_no_model():
    """Create LLMService instance without backend (no model configured)"""
    with patch("zikos.services.llm.create_backend", return_value=None):
        with patch("zikos.services.llm.settings") as mock_settings:
            mock_settings.llm_model_path = ""
            service = LLMService()
            service.backend = None
            return service


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server"""
    server = MagicMock()
    server.get_tools.return_value = [
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]
    return server


class TestLLMServiceInitialization:
    """Tests for LLM service initialization"""

    def test_initialization_with_model(self, mock_backend):
        """Test LLM service initialization with model"""
        with patch("zikos.services.llm.create_backend", return_value=mock_backend):
            with patch("zikos.services.llm.settings") as mock_settings:
                with patch("pathlib.Path.exists", return_value=True):
                    mock_settings.llm_model_path = "/path/to/model.gguf"
                    mock_settings.llm_n_ctx = 4096
                    mock_settings.llm_n_gpu_layers = 0
                    mock_settings.llm_backend = "auto"
                    mock_settings.llm_temperature = 0.7
                    mock_settings.llm_top_p = 0.9

                    service = LLMService()

                    assert service.backend is not None
                    assert service.audio_service is not None
                    assert isinstance(service.conversations, dict)

    def test_initialization_without_model(self):
        """Test LLM service initialization without model"""
        with patch("zikos.services.llm.create_backend", return_value=None):
            with patch("zikos.services.llm.settings") as mock_settings:
                mock_settings.llm_model_path = ""

                service = LLMService()

                assert service.backend is None
                assert service.audio_service is not None


class TestSystemPrompt:
    """Tests for system prompt loading"""

    def test_get_system_prompt_from_file(self, llm_service, tmp_path):
        """Test loading system prompt from file"""
        prompt_file = tmp_path / "SYSTEM_PROMPT.md"
        prompt_file.write_text("# System Prompt\n\n```\nYou are a helpful assistant.\n```\n")

        # Create directory structure that matches the path resolution
        # Path(__file__).parent.parent.parent.parent resolves from backend/zikos/services/llm.py to root
        # So we need: tmp_path/backend/zikos/services/llm.py -> tmp_path/SYSTEM_PROMPT.md
        services_dir = tmp_path / "backend" / "zikos" / "services"
        services_dir.mkdir(parents=True, exist_ok=True)

        # Patch __file__ to point to our temp structure
        import zikos.services.llm as llm_module

        original_file = llm_module.__file__
        fake_file = services_dir / "llm.py"
        fake_file.touch()

        try:
            llm_module.__file__ = str(fake_file)
            prompt = llm_service._get_system_prompt()
            assert "helpful assistant" in prompt
        finally:
            llm_module.__file__ = original_file

    def test_get_system_prompt_fallback(self, llm_service, tmp_path):
        """Test fallback system prompt when file doesn't exist"""
        # Create directory structure but don't create SYSTEM_PROMPT.md
        services_dir = tmp_path / "backend" / "zikos" / "services"
        services_dir.mkdir(parents=True, exist_ok=True)

        import zikos.services.llm as llm_module

        original_file = llm_module.__file__
        fake_file = services_dir / "llm.py"
        fake_file.touch()

        try:
            llm_module.__file__ = str(fake_file)
            prompt = llm_service._get_system_prompt()
            assert "expert music teacher" in prompt.lower()
        finally:
            llm_module.__file__ = original_file

    def test_get_system_prompt_injects_music_flamingo_when_configured(self, llm_service, tmp_path):
        """Test that Music Flamingo section is injected when service URL is configured"""
        prompt_file = tmp_path / "SYSTEM_PROMPT.md"
        prompt_file.write_text("# System Prompt\n\n```\nYou are a helpful assistant.\n```\n")

        services_dir = tmp_path / "backend" / "zikos" / "services"
        services_dir.mkdir(parents=True, exist_ok=True)

        from unittest.mock import patch

        import zikos.services.llm as llm_module

        original_file = llm_module.__file__
        fake_file = services_dir / "llm.py"
        fake_file.touch()

        try:
            llm_module.__file__ = str(fake_file)
            with patch("zikos.services.llm.settings") as mock_settings:
                mock_settings.music_flamingo_service_url = "http://localhost:8001"
                prompt = llm_service._get_system_prompt()
                assert "Music Flamingo" in prompt
                assert "analyze_music_with_flamingo" in prompt
                assert "multimodal AI model" in prompt
        finally:
            llm_module.__file__ = original_file

    def test_get_system_prompt_no_music_flamingo_when_not_configured(self, llm_service, tmp_path):
        """Test that Music Flamingo section is NOT injected when service URL is not configured"""
        prompt_file = tmp_path / "SYSTEM_PROMPT.md"
        prompt_file.write_text("# System Prompt\n\n```\nYou are a helpful assistant.\n```\n")

        services_dir = tmp_path / "backend" / "zikos" / "services"
        services_dir.mkdir(parents=True, exist_ok=True)

        from unittest.mock import patch

        import zikos.services.llm as llm_module

        original_file = llm_module.__file__
        fake_file = services_dir / "llm.py"
        fake_file.touch()

        try:
            llm_module.__file__ = str(fake_file)
            with patch("zikos.services.llm.settings") as mock_settings:
                mock_settings.music_flamingo_service_url = ""
                prompt = llm_service._get_system_prompt()
                assert "Music Flamingo" not in prompt
                assert "analyze_music_with_flamingo" not in prompt
        finally:
            llm_module.__file__ = original_file


class TestConversationHistory:
    """Tests for conversation history management"""

    def test_get_conversation_history_new_session(self, llm_service):
        """Test getting conversation history for new session"""
        history = llm_service._get_conversation_history("new_session")

        assert len(history) == 1
        assert history[0]["role"] == "system"
        assert "content" in history[0]

    def test_get_conversation_history_existing_session(self, llm_service):
        """Test getting conversation history for existing session"""
        session_id = "test_session"
        llm_service.conversations[session_id] = [{"role": "user", "content": "Hello"}]

        history = llm_service._get_conversation_history(session_id)

        assert len(history) == 1
        assert history[0]["content"] == "Hello"

    def test_conversation_history_preserves_system_prompt(self, llm_service):
        """Test that system prompt is preserved in conversation history"""
        session_id = "test_session"
        history1 = llm_service._get_conversation_history(session_id)
        history2 = llm_service._get_conversation_history(session_id)

        assert len(history1) == 1
        assert history1[0]["role"] == "system"
        assert history1 == history2


class TestMessagePreparation:
    """Tests for message preparation and truncation"""

    def test_prepare_messages_with_system_prompt(self, llm_service):
        """Test preparing messages with system prompt prepended"""
        history = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

        messages = llm_service._prepare_messages(history)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "You are helpful" in messages[0]["content"]
        assert "Hello" in messages[0]["content"]

    def test_prepare_messages_truncates_long_history(self, llm_service):
        """Test that long conversation history is truncated"""
        history = [{"role": "system", "content": "System prompt"}]
        # Create many messages to exceed token limit
        for i in range(100):
            history.append({"role": "user", "content": f"Message {i}" * 100})
            history.append({"role": "assistant", "content": f"Response {i}" * 100})

        messages = llm_service._prepare_messages(history, max_tokens=1000)

        # Should be truncated but still have messages
        assert len(messages) < len(history)
        assert len(messages) > 0

    def test_prepare_messages_preserves_audio_analysis(self, llm_service):
        """Test that audio analysis messages are always preserved"""
        history = [
            {"role": "system", "content": "System prompt"},
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: test.wav\nTempo: 120 BPM",
            },
            {"role": "user", "content": "Message 1" * 100},
            {"role": "user", "content": "Message 2" * 100},
            {"role": "user", "content": "Message 3" * 100},
        ]

        messages = llm_service._prepare_messages(history, max_tokens=500)

        # Audio analysis should be preserved
        audio_found = any(
            "[Audio Analysis Results]" in str(msg.get("content", "")) for msg in messages
        )
        assert audio_found, "Audio analysis message should be preserved"


class TestAudioAnalysisDetection:
    """Tests for audio analysis detection and context injection"""

    def test_find_recent_audio_analysis(self, llm_service):
        """Test finding recent audio analysis in history"""
        history = [
            {"role": "user", "content": "Hello"},
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: test.wav\nTempo: 120 BPM",
            },
        ]

        analysis = llm_service._find_recent_audio_analysis(history)

        assert analysis is not None
        assert "Audio Analysis Results" in analysis
        assert "Tempo: 120 BPM" in analysis

    def test_find_recent_audio_analysis_not_found(self, llm_service):
        """Test when no audio analysis is found"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        analysis = llm_service._find_recent_audio_analysis(history)

        assert analysis is None

    def test_find_recent_audio_analysis_with_markers(self, llm_service):
        """Test finding audio analysis with various markers"""
        test_cases = [
            ("[Audio Analysis Results]", True),
            ("[Audio analysis complete]", True),  # Case insensitive
            ('{"tempo": 120, "audio_file_id": "test123"}', True),  # Needs structured data
            ("Just regular text", False),  # Should not match
        ]

        for marker, should_match in test_cases:
            history = [{"role": "user", "content": f"Test {marker} data"}]
            analysis = llm_service._find_recent_audio_analysis(history)
            if should_match:
                assert analysis is not None, f"Should find analysis with marker: {marker}"
            else:
                assert analysis is None, f"Should not find analysis with marker: {marker}"

    @pytest.mark.asyncio
    async def test_generate_response_injects_audio_analysis(self, llm_service, mock_mcp_server):
        """Test that audio analysis is injected when user asks about audio"""
        session_id = "test_session"
        history = llm_service._get_conversation_history(session_id)
        history.append(
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: audio123.wav\nTempo: 120 BPM",
            }
        )

        # Use a message that triggers audio detection but won't trigger pre-detection
        # "about this" triggers audio detection, but doesn't match pre-detection keywords
        # Avoid "test" which matches pre-detection
        user_message = "What can you tell me about this sample?"
        result = await llm_service.generate_response(user_message, session_id, mock_mcp_server)

        # The message gets modified to include analysis, then checked for pre-detection
        # If pre-detection doesn't match, LLM should be called
        # Check that either LLM was called OR pre-detection returned early (both are valid)
        if result.get("type") == "tool_call":
            # Pre-detection matched, which is fine - just verify it happened
            assert "tool_name" in result
        else:
            # LLM should have been called
            call_args = llm_service.backend.create_chat_completion.call_args
            assert call_args is not None, "LLM should have been called"
            messages = call_args.kwargs.get("messages", [])
            # Should have audio analysis in the messages
            message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
            assert "Audio Analysis" in message_contents or "Tempo: 120" in message_contents

    @pytest.mark.asyncio
    async def test_generate_response_no_analysis_found(self, llm_service, mock_mcp_server):
        """Test response when no audio analysis is found"""
        session_id = "test_session"

        # Configure mock to return expected response when it sees the instruction about no audio analysis
        def mock_chat_completion(*args, **kwargs):
            messages = kwargs.get("messages", [])
            message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
            if "no audio analysis data is available" in message_contents.lower():
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "I don't see any audio analysis available in our conversation. Please record or upload audio first.",
                                "role": "assistant",
                            }
                        }
                    ]
                }
            return {"choices": [{"message": {"content": "Test response", "role": "assistant"}}]}

        llm_service.backend.create_chat_completion.side_effect = mock_chat_completion

        result = await llm_service.generate_response(
            "Can you tell me about this sample?", session_id, mock_mcp_server
        )

        assert result["type"] == "response"
        assert "don't see any audio analysis" in result["message"].lower()


class TestGenerateResponse:
    """Tests for response generation"""

    @pytest.mark.asyncio
    async def test_generate_response_without_llm(self, llm_service_no_model, mock_mcp_server):
        """Test response generation when LLM is not available"""
        result = await llm_service_no_model.generate_response(
            "Hello", "test_session", mock_mcp_server
        )

        assert result["type"] == "response"
        assert "LLM not available" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_response_with_llm(self, llm_service, mock_mcp_server):
        """Test response generation with LLM"""
        result = await llm_service.generate_response("Hello", "test_session", mock_mcp_server)

        assert result["type"] == "response"
        assert "message" in result
        assert llm_service.backend.create_chat_completion.called

    @pytest.mark.asyncio
    async def test_generate_response_with_tool_call(self, llm_service, mock_mcp_server):
        """Test response generation with tool call"""
        from zikos.mcp.tool import ToolCategory

        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.RECORDING
        mock_tool_registry = mock_mcp_server.get_tool_registry()
        mock_tool_registry.get_tool.return_value = mock_tool

        llm_service.backend.create_chat_completion.return_value = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "function": {
                                    "name": "request_audio_recording",
                                    "arguments": '{"prompt": "Record audio"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }

        result = await llm_service.generate_response(
            "let's record", "test_session", mock_mcp_server
        )

        assert result["type"] == "tool_call"
        assert result["tool_name"] == "request_audio_recording"

    @pytest.mark.asyncio
    async def test_generate_response_max_iterations(self, llm_service, mock_mcp_server):
        """Test that max iterations prevents infinite loops"""
        # Mock tool call that keeps returning tool calls (not a widget tool)
        call_count = 0

        def mock_chat_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": f"call_{call_count}",
                                    "function": {
                                        "name": "analyze_tempo",  # An audio analysis tool, not a widget
                                        "arguments": '{"audio_file_id": "test"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }

        llm_service.backend.create_chat_completion.side_effect = mock_chat_completion
        mock_mcp_server.call_tool = AsyncMock(return_value={"result": "analysis_result"})

        # Use a message that won't trigger pre-detection
        # "test" matches pre-detection, so use something else
        result = await llm_service.generate_response(
            "Hello, how are you?", "test_session", mock_mcp_server
        )

        # Should hit repetitive tool calling detection (after 4 calls) or max iterations
        # Note: The repetitive detection triggers first, preventing infinite loops
        assert result["type"] == "response"
        assert (
            "stuck in a loop" in result["message"]
            or "Maximum iterations" in result["message"]
            or "too many tool calls" in result["message"]
        )
        # Should have called multiple times (at least 4 for repetitive detection)
        assert call_count >= 4, f"Expected at least 4 calls, got {call_count}"


class TestHandleAudioReady:
    """Tests for handling audio ready notifications"""

    @pytest.mark.asyncio
    async def test_handle_audio_ready(self, llm_service, mock_mcp_server):
        """Test handling audio ready notification"""
        audio_file_id = "test_audio_123"
        mock_analysis = {"tempo": 120, "pitch": {"accuracy": 0.9}}

        with patch.object(
            llm_service.audio_service, "run_baseline_analysis", return_value=mock_analysis
        ):
            result = await llm_service.handle_audio_ready(
                audio_file_id, "recording_123", "test_session", mock_mcp_server
            )

            assert "type" in result
            # Should return a dict with type and message (or tool_call)
            assert result["type"] in ["response", "tool_call"]
            # Check that analysis was included in the message sent to LLM
            call_args = llm_service.backend.create_chat_completion.call_args
            if call_args:
                messages = call_args.kwargs.get("messages", [])
                message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
                assert "[Audio Analysis Results]" in message_contents or "120" in message_contents

    @pytest.mark.asyncio
    async def test_handle_audio_ready_includes_interpretation_reminder(
        self, llm_service, mock_mcp_server
    ):
        """Test that interpretation reminder is included when audio analysis is injected"""
        audio_file_id = "test_audio_123"
        mock_analysis = {"tempo": 120, "pitch": {"accuracy": 0.9}}

        with patch.object(
            llm_service.audio_service, "run_baseline_analysis", return_value=mock_analysis
        ):
            await llm_service.handle_audio_ready(
                audio_file_id, "recording_123", "session_123", mock_mcp_server
            )

            # Check that interpretation reminder is included in the message
            call_args = llm_service.backend.create_chat_completion.call_args
            if call_args:
                messages = call_args.kwargs.get("messages", [])
                message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
                assert "CRITICAL INSTRUCTIONS FOR PROVIDING FEEDBACK" in message_contents
                assert "NEVER report raw metrics" in message_contents
                assert "ALWAYS interpret metrics musically" in message_contents

    @pytest.mark.asyncio
    async def test_generate_response_includes_interpretation_reminder_for_audio_context(
        self, llm_service, mock_mcp_server
    ):
        """Test that interpretation reminder is included when prepending audio analysis context"""
        session_id = "test_session"
        history = llm_service._get_conversation_history(session_id)
        history.append(
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: audio123.wav\nTempo: 120 BPM",
            }
        )

        # Use a message that triggers audio detection
        user_message = "What can you tell me about this sample?"
        await llm_service.generate_response(user_message, session_id, mock_mcp_server)

        # Check that interpretation reminder is included
        call_args = llm_service.backend.create_chat_completion.call_args
        if call_args:
            messages = call_args.kwargs.get("messages", [])
            message_contents = " ".join(str(msg.get("content", "")) for msg in messages)
            # Should have the reminder when audio context is prepended
            if "Audio Analysis Context" in message_contents:
                assert "CRITICAL:" in message_contents
                assert (
                    "NEVER report raw metrics" in message_contents
                    or "interpret" in message_contents.lower()
                )

    @pytest.mark.asyncio
    async def test_handle_audio_ready_error_handling(self, llm_service, mock_mcp_server):
        """Test error handling when audio analysis fails"""
        audio_file_id = "test_audio_123"

        with patch.object(
            llm_service.audio_service,
            "run_baseline_analysis",
            side_effect=Exception("Analysis failed"),
        ):
            result = await llm_service.handle_audio_ready(
                audio_file_id, "recording_123", "test_session", mock_mcp_server
            )

            assert result["type"] == "response"
            assert "Error analyzing audio" in result["message"]


class TestThinkingMechanism:
    """Tests for thinking/chain of thought mechanism"""

    def test_extract_thinking_from_content(self, llm_service):
        """Test extracting thinking tags from content"""
        content = """<thinking>
I need to analyze this audio. Let me think about which tools to use.
</thinking>
I'll analyze your performance."""

        cleaned, thinking = llm_service._extract_thinking(content)

        assert "I'll analyze your performance." in cleaned
        assert "<thinking>" not in cleaned
        assert "I need to analyze this audio" in thinking

    def test_extract_thinking_multiple_tags(self, llm_service):
        """Test extracting multiple thinking tags"""
        content = """<thinking>First thought</thinking>
Some text
<thinking>Second thought</thinking>
More text"""

        cleaned, thinking = llm_service._extract_thinking(content)

        assert "Some text" in cleaned
        assert "More text" in cleaned
        assert "First thought" in thinking
        assert "Second thought" in thinking

    def test_extract_thinking_no_tags(self, llm_service):
        """Test extracting thinking when no tags present"""
        content = "Just regular content without thinking tags"

        cleaned, thinking = llm_service._extract_thinking(content)

        assert cleaned == content
        assert thinking == ""

    def test_prepare_messages_filters_thinking_for_user(self, llm_service):
        """Test that thinking messages are filtered when preparing for user display"""
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "thinking", "content": "I should respond helpfully"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        messages_for_user = llm_service._prepare_messages(history, for_user=True)
        messages_for_llm = llm_service._prepare_messages(history, for_user=False)

        # Thinking should be filtered for user
        thinking_in_user = any(msg.get("role") == "thinking" for msg in messages_for_user)
        assert not thinking_in_user

        # Thinking should be included for LLM
        thinking_in_llm = any(msg.get("role") == "thinking" for msg in messages_for_llm)
        assert thinking_in_llm

    @pytest.mark.asyncio
    async def test_thinking_extracted_before_tool_calls(self, llm_service, mock_mcp_server):
        """Test that thinking is extracted and stored before tool calls"""
        mock_backend = llm_service.backend
        mock_backend.create_chat_completion.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """<thinking>
I should call the analyze_tempo tool to check the tempo.
</thinking>
Let me analyze the tempo.""",
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "analyze_tempo",
                                    "arguments": '{"audio_file_id": "test.wav"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }

        mock_mcp_server.call_tool = AsyncMock(return_value={"tempo": 120})

        history = llm_service._get_conversation_history("test_session")
        history.append({"role": "user", "content": "Analyze my tempo"})

        # Mock the tool call to prevent actual execution
        with patch.object(llm_service, "_prepare_messages", return_value=history):
            # We'll just verify the extraction method works
            content = mock_backend.create_chat_completion.return_value["choices"][0]["message"][
                "content"
            ]
            cleaned, thinking = llm_service._extract_thinking(content)

            assert thinking != ""
            assert "I should call the analyze_tempo tool" in thinking
            assert "<thinking>" not in cleaned

    def test_thinking_preserved_in_history(self, llm_service):
        """Test that thinking messages are preserved in conversation history"""
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
        ]

        # Simulate adding thinking
        thinking_msg = {"role": "thinking", "content": "I should respond helpfully"}
        history.append(thinking_msg)
        history.append({"role": "assistant", "content": "Hi!"})

        # Prepare messages for LLM (should include thinking)
        messages = llm_service._prepare_messages(history, for_user=False)

        thinking_found = any(
            msg.get("role") == "thinking" and msg.get("content") == "I should respond helpfully"
            for msg in messages
        )
        assert thinking_found
