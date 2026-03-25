"""Tests for LLM service"""

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.helpers.fake_backend import FakeBackend
from zikos.mcp.server import MCPServer
from zikos.services.llm import LLMService


def make_llm_service(response: str = "Test response", **backend_kwargs) -> LLMService:
    """Create LLMService with a FakeBackend, bypassing model file checks."""
    backend = FakeBackend(response, **backend_kwargs)
    backend.initialize(model_path="fake.gguf", n_ctx=4096)

    with patch("zikos.services.llm_init.create_backend", return_value=backend):
        with patch("zikos.services.llm.settings") as mock_settings:
            mock_settings.llm_model_path = ""
            service = LLMService()
            service.backend = backend
            return service


@pytest.fixture
def llm_service():
    return make_llm_service()


@pytest.fixture
def mcp_server():
    return MCPServer()


class TestInitialization:
    def test_with_backend(self):
        service = make_llm_service()
        assert service.backend is not None
        assert service.backend.is_initialized()
        assert service.audio_service is not None
        assert isinstance(service.conversations, dict)

    def test_without_model(self):
        with patch("zikos.services.llm_init.create_backend", return_value=None):
            with patch("zikos.services.llm.settings") as s:
                s.llm_model_path = ""
                service = LLMService()

        assert service.backend is None
        assert service.initialization_error is not None


class TestSystemPrompt:
    def test_loads_from_file(self, llm_service, tmp_path):
        prompt_file = tmp_path / "SYSTEM_PROMPT.md"
        prompt_file.write_text("# Prompt\n\n```\nYou are a helpful assistant.\n```\n")

        prompt = llm_service._get_system_prompt(prompt_file_path=prompt_file)
        assert "helpful assistant" in prompt

    def test_fallback_when_file_missing(self, llm_service, tmp_path):
        prompt = llm_service._get_system_prompt(prompt_file_path=tmp_path / "NONEXISTENT.md")
        assert "expert music teacher" in prompt.lower()


class TestConversationHistory:
    def test_new_session_has_system_prompt(self, llm_service):
        history = llm_service._get_conversation_history("new_session")

        assert len(history) == 1
        assert history[0]["role"] == "system"

    def test_existing_session_preserved(self, llm_service):
        llm_service.conversations["s1"] = [{"role": "user", "content": "Hello"}]
        history = llm_service._get_conversation_history("s1")

        assert len(history) == 1
        assert history[0]["content"] == "Hello"

    def test_same_session_returns_same_history(self, llm_service):
        h1 = llm_service._get_conversation_history("s1")
        h2 = llm_service._get_conversation_history("s1")
        assert h1 is h2


class TestMessagePreparation:
    def test_includes_system_and_user_messages(self, llm_service):
        history = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        messages = llm_service._prepare_messages(history)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "Hello"

    def test_truncates_long_history(self, llm_service):
        history = [{"role": "system", "content": "System prompt"}]
        for i in range(100):
            history.append({"role": "user", "content": f"Message {i}" * 100})
            history.append({"role": "assistant", "content": f"Response {i}" * 100})

        messages = llm_service._prepare_messages(history, max_tokens=1000)
        assert len(messages) < len(history)
        assert len(messages) > 0

    def test_preserves_audio_analysis(self, llm_service):
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

        audio_found = any("[Audio Analysis Results]" in str(m.get("content", "")) for m in messages)
        assert audio_found

    def test_filters_thinking_for_user(self, llm_service):
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "thinking", "content": "I should respond helpfully"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        for_user = llm_service._prepare_messages(history, for_user=True)
        for_llm = llm_service._prepare_messages(history, for_user=False)

        assert not any(m.get("role") == "thinking" for m in for_user)
        assert any(m.get("role") == "thinking" for m in for_llm)


class TestAudioAnalysisDetection:
    def test_finds_analysis_in_history(self, llm_service):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "[Audio Analysis Results]\nTempo: 120 BPM"},
        ]
        analysis = llm_service._find_recent_audio_analysis(history)

        assert analysis is not None
        assert "120 BPM" in analysis

    def test_returns_none_when_no_analysis(self, llm_service):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        assert llm_service._find_recent_audio_analysis(history) is None


class TestGenerateResponse:
    @pytest.mark.asyncio
    async def test_returns_error_without_backend(self, mcp_server):
        with patch("zikos.services.llm_init.create_backend", return_value=None):
            with patch("zikos.services.llm.settings") as s:
                s.llm_model_path = ""
                service = LLMService()

        result = await service.generate_response("Hello", "s1", mcp_server)
        assert result["type"] == "error"
        assert "not available" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_returns_response_from_backend(self, mcp_server):
        service = make_llm_service("Here is my analysis of your performance.")

        result = await service.generate_response("How did I do?", "s1", mcp_server)

        assert result["type"] == "response"
        assert "analysis" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_backend_receives_user_message(self, mcp_server):
        service = make_llm_service("OK")

        await service.generate_response("Play a C scale", "s1", mcp_server)

        assert len(service.backend.messages_received) > 0
        all_msgs = service.backend.messages_received[0]
        user_msgs = [m for m in all_msgs if m["role"] == "user"]
        assert any("C scale" in m["content"] for m in user_msgs)

    @pytest.mark.asyncio
    async def test_tool_call_response(self, mcp_server):
        service = make_llm_service(
            response="",
            tool_calls=[
                {
                    "id": "call_1",
                    "function": {
                        "name": "request_audio_recording",
                        "arguments": '{"prompt": "Record audio"}',
                    },
                }
            ],
        )

        result = await service.generate_response("Let's record", "s1", mcp_server)

        assert result["type"] == "tool_call"
        assert result["tool_name"] == "request_audio_recording"


class TestHandleAudioReady:
    @pytest.mark.asyncio
    async def test_injects_analysis_into_message(self, mcp_server):
        service = make_llm_service("Your tempo is steady at 120 BPM.")
        mock_analysis = {"tempo": 120, "pitch": {"accuracy": 0.9}}

        with patch.object(
            service.audio_service, "run_baseline_analysis", return_value=mock_analysis
        ):
            result = await service.handle_audio_ready("audio_1", "rec_1", "s1", mcp_server)

        assert result["type"] in ("response", "tool_call")
        history = service._get_conversation_history("s1")
        user_msgs = [m for m in history if m["role"] == "user"]
        last_msg = user_msgs[-1]["content"]
        assert "[Audio Analysis Results]" in last_msg or "120" in last_msg

    @pytest.mark.asyncio
    async def test_includes_interpretation_reminder(self, mcp_server):
        service = make_llm_service("Great job!")
        mock_analysis = {"tempo": 120}

        with patch.object(
            service.audio_service, "run_baseline_analysis", return_value=mock_analysis
        ):
            await service.handle_audio_ready("audio_1", "rec_1", "s1", mcp_server)

        history = service._get_conversation_history("s1")
        user_msgs = [m for m in history if m["role"] == "user"]
        last_msg = user_msgs[-1]["content"]
        assert "CRITICAL INSTRUCTIONS FOR PROVIDING FEEDBACK" in last_msg

    @pytest.mark.asyncio
    async def test_error_handling(self, mcp_server):
        service = make_llm_service("I encountered an error analyzing the audio file.")

        with patch.object(
            service.audio_service,
            "run_baseline_analysis",
            side_effect=Exception("Analysis failed"),
        ):
            result = await service.handle_audio_ready("audio_1", "rec_1", "s1", mcp_server)

        assert result["type"] == "response"


class TestThinking:
    def test_extract_thinking_from_content(self, llm_service):
        content = "<thinking>\nLet me analyze this.\n</thinking>\nGreat performance!"

        cleaned, thinking = llm_service._extract_thinking(content)

        assert "Great performance!" in cleaned
        assert "<thinking>" not in cleaned
        assert "analyze this" in thinking

    def test_extract_multiple_thinking_tags(self, llm_service):
        content = "<thinking>First</thinking>\nText\n<thinking>Second</thinking>\nMore"

        cleaned, thinking = llm_service._extract_thinking(content)

        assert "Text" in cleaned
        assert "More" in cleaned
        assert "First" in thinking
        assert "Second" in thinking

    def test_no_thinking_tags(self, llm_service):
        content = "Just regular content"
        cleaned, thinking = llm_service._extract_thinking(content)

        assert cleaned == content
        assert thinking == ""

    def test_thinking_preserved_in_history_for_llm(self, llm_service):
        history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
            {"role": "thinking", "content": "I should respond helpfully"},
            {"role": "assistant", "content": "Hi!"},
        ]
        messages = llm_service._prepare_messages(history, for_user=False)

        assert any(
            m.get("role") == "thinking" and "respond helpfully" in m.get("content", "")
            for m in messages
        )
