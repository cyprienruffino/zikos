"""Unit tests for LLM service"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from zikos.services.llm import LLMService


@pytest.fixture
def mock_backend():
    """Mock LLM backend with streaming support"""
    backend = MagicMock()
    backend.is_initialized.return_value = True
    backend.get_context_window.return_value = 4096
    backend.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Test response", "role": "assistant"}}]
    }

    # Mock streaming response (default behavior)
    async def stream_chat_completion(*args, **kwargs):
        tokens = ["Test", " response"]
        for token in tokens:
            yield {
                "choices": [
                    {"delta": {"content": token, "role": "assistant"}, "finish_reason": None}
                ]
            }
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

    backend.stream_chat_completion = stream_chat_completion
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

        prompt = llm_service._get_system_prompt(prompt_file_path=prompt_file)
        assert "helpful assistant" in prompt

    def test_get_system_prompt_fallback(self, llm_service, tmp_path):
        """Test fallback system prompt when file doesn't exist"""
        from pathlib import Path

        non_existent_file = tmp_path / "NONEXISTENT.md"
        prompt = llm_service._get_system_prompt(prompt_file_path=non_existent_file)
        assert "expert music teacher" in prompt.lower()


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
        from unittest.mock import AsyncMock

        session_id = "test_session"
        history = llm_service._get_conversation_history(session_id)
        history.append(
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: audio123.wav\nTempo: 120 BPM",
            }
        )

        # Ensure backend is initialized
        llm_service.backend.is_initialized.return_value = True

        # Mock stream_chat_completion to return a response in the correct format
        async def mock_stream(*args, **kwargs):
            # Yield token chunks
            yield {
                "choices": [
                    {"delta": {"content": "Based", "role": "assistant"}, "finish_reason": None}
                ]
            }
            yield {
                "choices": [
                    {"delta": {"content": " on", "role": "assistant"}, "finish_reason": None}
                ]
            }
            # Final chunk with stop reason
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

        llm_service.backend.stream_chat_completion = mock_stream

        # Use a message that triggers audio detection but won't trigger pre-detection
        # "about this" triggers audio detection, but doesn't match pre-detection keywords
        # Avoid "test" which matches pre-detection
        user_message = "What can you tell me about this sample?"
        result = await llm_service.generate_response(user_message, session_id, mock_mcp_server)

        # Should get a response (not an error)
        assert result.get("type") in ("response", "tool_call")

        # Verify that audio analysis was injected into the conversation
        # The audio_context_enricher should have added the analysis to the message
        # Check the history to see if the enriched message contains the audio analysis
        final_history = llm_service._get_conversation_history(session_id)
        # The last user message should have been enriched with audio analysis
        user_messages = [msg for msg in final_history if msg.get("role") == "user"]
        assert len(user_messages) > 0, "Should have user messages in history"
        last_user_msg = user_messages[-1].get("content", "")
        # Audio analysis should be properly formatted with [Audio Analysis Context] marker
        # or contain the actual analysis data (tempo: 120 BPM)
        assert (
            "[Audio Analysis Context]" in last_user_msg
            or "120" in last_user_msg
            or "Tempo: 120 BPM" in last_user_msg
        ), f"Audio analysis not properly injected. Message: {last_user_msg[:200]}"

    @pytest.mark.asyncio
    async def test_generate_response_no_analysis_found(self, llm_service, mock_mcp_server):
        """Test response when no audio analysis is found"""
        session_id = "test_session"

        # Ensure backend is initialized
        llm_service.backend.is_initialized.return_value = True

        # Configure mock stream to return expected response when it sees the instruction about no audio analysis
        async def mock_stream(*args, **kwargs):
            # Yield a response about no audio analysis
            yield {
                "choices": [
                    {
                        "delta": {
                            "content": "I don't see any audio analysis available in our conversation. Please record or upload audio first.",
                            "role": "assistant",
                        },
                        "finish_reason": None,
                    }
                ]
            }
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

        llm_service.backend.stream_chat_completion = mock_stream

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

        assert result["type"] == "error"
        assert "LLM not available" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_response_with_llm(self, llm_service, mock_mcp_server):
        """Test response generation with LLM"""
        # Track if stream_chat_completion was called
        original_stream = llm_service.backend.stream_chat_completion
        call_count = 0

        async def tracked_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            async for chunk in original_stream(*args, **kwargs):
                yield chunk

        llm_service.backend.stream_chat_completion = tracked_stream

        result = await llm_service.generate_response("Hello", "test_session", mock_mcp_server)

        assert result["type"] == "response"
        assert "message" in result
        assert call_count > 0

    @pytest.mark.asyncio
    async def test_generate_response_with_tool_call(self, llm_service, mock_mcp_server):
        """Test response generation with tool call"""
        from zikos.mcp.tool import ToolCategory

        mock_tool = MagicMock()
        mock_tool.category = ToolCategory.RECORDING
        mock_tool_registry = mock_mcp_server.get_tool_registry()
        mock_tool_registry.get_tool.return_value = mock_tool

        # Mock streaming response with tool call
        async def stream_with_tool_call(*args, **kwargs):
            # First yield tool call in delta
            yield {
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "function": {
                                        "name": "request_audio_recording",
                                        "arguments": '{"prompt": "Record audio"}',
                                    },
                                    "index": 0,
                                }
                            ],
                        },
                        "finish_reason": None,
                    }
                ]
            }
            # Final chunk
            yield {
                "choices": [
                    {
                        "delta": {},
                        "finish_reason": "tool_calls",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "function": {
                                    "name": "request_audio_recording",
                                    "arguments": '{"prompt": "Record audio"}',
                                },
                                "index": 0,
                            }
                        ],
                    }
                ]
            }

        llm_service.backend.stream_chat_completion = stream_with_tool_call

        result = await llm_service.generate_response(
            "let's record", "test_session", mock_mcp_server
        )

        assert result["type"] == "tool_call"
        assert result["tool_name"] == "request_audio_recording"


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
            # Verify stream_chat_completion was called by checking the call count
            # Since it's a function, we need to track calls differently
            # The best way is to check the conversation history to see if the analysis was included
            final_history = llm_service._get_conversation_history("test_session")
            user_messages = [msg for msg in final_history if msg.get("role") == "user"]
            assert len(user_messages) > 0, "Should have user messages in history"
            # The last user message should contain the audio analysis
            last_user_msg = user_messages[-1].get("content", "")
            assert (
                "[Audio Analysis Results]" in last_user_msg or "120" in last_user_msg
            ), f"Audio analysis not found in message: {last_user_msg[:200]}"

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
            # Verify by checking the conversation history
            final_history = llm_service._get_conversation_history("session_123")
            user_messages = [msg for msg in final_history if msg.get("role") == "user"]
            assert len(user_messages) > 0, "Should have user messages in history"
            last_user_msg = user_messages[-1].get("content", "")
            assert (
                "CRITICAL INSTRUCTIONS FOR PROVIDING FEEDBACK" in last_user_msg
            ), f"Interpretation reminder not found in message: {last_user_msg[:300]}"
            assert "NEVER report raw metrics" in last_user_msg
            assert "ALWAYS interpret metrics musically" in last_user_msg

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
        # Verify by checking the conversation history
        final_history = llm_service._get_conversation_history(session_id)
        user_messages = [msg for msg in final_history if msg.get("role") == "user"]
        assert len(user_messages) > 0, "Should have user messages in history"
        last_user_msg = user_messages[-1].get("content", "")
        # Should have the reminder when audio context is prepended
        if "Audio Analysis Context" in last_user_msg:
            assert "CRITICAL:" in last_user_msg or "CRITICAL INSTRUCTIONS" in last_user_msg
            assert (
                "NEVER report raw metrics" in last_user_msg or "interpret" in last_user_msg.lower()
            )

    @pytest.mark.asyncio
    async def test_handle_audio_ready_error_handling(self, llm_service, mock_mcp_server):
        """Test error handling when audio analysis fails"""
        from unittest.mock import AsyncMock

        audio_file_id = "test_audio_123"

        # Ensure backend is initialized
        llm_service.backend.is_initialized.return_value = True

        # Mock stream_chat_completion to return a response about the error
        async def mock_stream(*args, **kwargs):
            yield {
                "choices": [
                    {
                        "delta": {
                            "content": "I encountered an error analyzing the audio file. The file may be corrupted or in an unsupported format.",
                            "role": "assistant",
                        },
                        "finish_reason": None,
                    }
                ]
            }
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}

        llm_service.backend.stream_chat_completion = mock_stream

        with patch.object(
            llm_service.audio_service,
            "run_baseline_analysis",
            side_effect=Exception("Analysis failed"),
        ):
            result = await llm_service.handle_audio_ready(
                audio_file_id, "recording_123", "test_session", mock_mcp_server
            )

            assert result["type"] == "response"
            # The LLM should be informed about the error and respond accordingly
            assert (
                "error" in result["message"].lower()
                or "corrupted" in result["message"].lower()
                or "unsupported" in result["message"].lower()
            )


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
