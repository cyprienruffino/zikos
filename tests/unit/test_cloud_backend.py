"""Tests for the CloudBackend (litellm-based)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.services.llm_backends.cloud import CloudBackend


@pytest.fixture
def backend() -> CloudBackend:
    b = CloudBackend()
    b.initialize(model_name="gpt-4o", api_key="test-key", temperature=0.7, top_p=0.9)
    return b


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_initialize_sets_state(backend: CloudBackend):
    assert backend.is_initialized()
    assert backend._model == "gpt-4o"
    assert backend._api_key == "test-key"
    assert backend._temperature == 0.7


def test_initialize_empty_api_key_becomes_none():
    b = CloudBackend()
    b.initialize(model_name="gpt-4o", api_key="")
    assert b._api_key is None


def test_not_initialized_before_initialize():
    assert not CloudBackend().is_initialized()


def test_close_is_noop(backend: CloudBackend):
    backend.close()
    assert backend.is_initialized()


# ---------------------------------------------------------------------------
# Context window
# ---------------------------------------------------------------------------


def test_get_context_window_from_litellm(backend: CloudBackend):
    with patch("zikos.services.llm_backends.cloud.litellm.get_model_info") as mock_info:
        mock_info.return_value = {"max_input_tokens": 128000}
        assert backend.get_context_window() == 128000


def test_get_context_window_falls_back_on_error(backend: CloudBackend):
    with patch("zikos.services.llm_backends.cloud.litellm.get_model_info", side_effect=Exception):
        assert backend.get_context_window() == 128000


def test_get_context_window_uses_max_tokens_fallback(backend: CloudBackend):
    with patch("zikos.services.llm_backends.cloud.litellm.get_model_info") as mock_info:
        mock_info.return_value = {"max_tokens": 32000}
        assert backend.get_context_window() == 32000


# ---------------------------------------------------------------------------
# create_chat_completion
# ---------------------------------------------------------------------------


def _make_completion_response(content: str = "Hello!", finish_reason: str = "stop") -> MagicMock:
    response = MagicMock()
    response.model_dump.return_value = {
        "choices": [
            {
                "message": {"role": "assistant", "content": content, "tool_calls": None},
                "finish_reason": finish_reason,
            }
        ]
    }
    return response


def test_create_chat_completion_basic(backend: CloudBackend):
    messages = [{"role": "user", "content": "Hi"}]
    with patch("zikos.services.llm_backends.cloud.litellm.completion") as mock_comp:
        mock_comp.return_value = _make_completion_response("Hello!")
        result = backend.create_chat_completion(messages)

    assert result["choices"][0]["message"]["content"] == "Hello!"
    call_kwargs = mock_comp.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["api_key"] == "test-key"
    assert call_kwargs["messages"] == messages


def test_create_chat_completion_passes_tools(backend: CloudBackend):
    tools = [{"type": "function", "function": {"name": "analyze_tempo", "parameters": {}}}]
    with patch("zikos.services.llm_backends.cloud.litellm.completion") as mock_comp:
        mock_comp.return_value = _make_completion_response()
        backend.create_chat_completion([{"role": "user", "content": "hi"}], tools=tools)

    assert mock_comp.call_args.kwargs["tools"] == tools


def test_create_chat_completion_no_tools_key_when_none(backend: CloudBackend):
    with patch("zikos.services.llm_backends.cloud.litellm.completion") as mock_comp:
        mock_comp.return_value = _make_completion_response()
        backend.create_chat_completion([{"role": "user", "content": "hi"}], tools=None)

    assert "tools" not in mock_comp.call_args.kwargs


def test_create_chat_completion_temperature_override(backend: CloudBackend):
    with patch("zikos.services.llm_backends.cloud.litellm.completion") as mock_comp:
        mock_comp.return_value = _make_completion_response()
        backend.create_chat_completion([{"role": "user", "content": "hi"}], temperature=0.1)

    assert mock_comp.call_args.kwargs["temperature"] == 0.1


# ---------------------------------------------------------------------------
# stream_chat_completion
# ---------------------------------------------------------------------------


def _make_chunk(content: str | None = None, tool_calls=None, finish_reason=None) -> MagicMock:
    """Build a mock litellm streaming chunk."""
    delta: dict[str, Any] = {}
    if content is not None:
        delta["content"] = content
    if tool_calls is not None:
        delta["tool_calls"] = tool_calls
    chunk = MagicMock()
    chunk.model_dump.return_value = {"choices": [{"delta": delta, "finish_reason": finish_reason}]}
    return chunk


async def _fake_stream(*chunks):
    """Async generator yielding the given chunks."""
    for c in chunks:
        yield c


@pytest.mark.asyncio
async def test_stream_chat_completion_content(backend: CloudBackend):
    stream = _fake_stream(
        _make_chunk(content="Hello"),
        _make_chunk(content=" world"),
        _make_chunk(finish_reason="stop"),
    )

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    content_chunks = [c for c in chunks if c["choices"][0]["delta"].get("content")]
    content = "".join(c["choices"][0]["delta"]["content"] for c in content_chunks)
    assert content == "Hello world"

    final = chunks[-1]["choices"][0]
    assert final["finish_reason"] == "stop"
    assert final["delta"] == {}


@pytest.mark.asyncio
async def test_stream_chat_completion_tool_calls_accumulated(backend: CloudBackend):
    stream = _fake_stream(
        _make_chunk(
            tool_calls=[
                {
                    "index": 0,
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "analyze_tempo", "arguments": ""},
                }
            ]
        ),
        _make_chunk(
            tool_calls=[{"index": 0, "function": {"arguments": '{"audio_file_id": "test.wav"}'}}]
        ),
        _make_chunk(finish_reason="tool_calls"),
    )

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    final = chunks[-1]["choices"][0]
    assert final["finish_reason"] == "tool_calls"
    tool_calls = final["tool_calls"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "analyze_tempo"
    assert '"audio_file_id"' in tool_calls[0]["function"]["arguments"]
    assert tool_calls[0]["id"] == "call_1"


@pytest.mark.asyncio
async def test_stream_chat_completion_no_tool_calls_in_final_when_none(backend: CloudBackend):
    stream = _fake_stream(
        _make_chunk(content="Done"),
        _make_chunk(finish_reason="stop"),
    )

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    final = chunks[-1]["choices"][0]
    assert "tool_calls" not in final


@pytest.mark.asyncio
async def test_stream_flushes_tool_calls_when_no_finish_reason(backend: CloudBackend):
    """A stream ending without finish_reason must flush accumulated tool
    calls instead of silently discarding them."""
    stream = _fake_stream(
        _make_chunk(
            tool_calls=[
                {
                    "index": 0,
                    "id": "call_x",
                    "type": "function",
                    "function": {"name": "detect_pitch", "arguments": "{}"},
                }
            ]
        ),
        # no finish_reason chunk — stream just ends
    )

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    final = chunks[-1]["choices"][0]
    assert final["finish_reason"] == "tool_calls"
    assert final["delta"]["tool_calls"][0]["id"] == "call_x"


@pytest.mark.asyncio
async def test_stream_without_finish_reason_and_no_tools_yields_stop(backend: CloudBackend):
    stream = _fake_stream(_make_chunk(content="hi"))

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_stream_tool_call_deltas_missing_index_not_merged(backend: CloudBackend):
    """Deltas without an index must become separate calls, not merge into slot 0."""
    stream = _fake_stream(
        _make_chunk(
            tool_calls=[
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "analyze_tempo", "arguments": "{}"},
                }
            ]
        ),
        _make_chunk(
            tool_calls=[
                {
                    "id": "c2",
                    "type": "function",
                    "function": {"name": "detect_pitch", "arguments": "{}"},
                }
            ]
        ),
        _make_chunk(finish_reason="tool_calls"),
    )

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    tool_calls = chunks[-1]["choices"][0]["tool_calls"]
    assert len(tool_calls) == 2
    assert {tc["id"] for tc in tool_calls} == {"c1", "c2"}
    assert {tc["function"]["name"] for tc in tool_calls} == {"analyze_tempo", "detect_pitch"}


@pytest.mark.asyncio
async def test_stream_skips_empty_choices_chunks(backend: CloudBackend):
    empty_chunk = MagicMock()
    empty_chunk.model_dump.return_value = {"choices": []}
    stream = _fake_stream(
        empty_chunk,
        _make_chunk(content="ok"),
        _make_chunk(finish_reason="stop"),
    )

    async def fake_acompletion(**kwargs):
        return stream

    with patch("zikos.services.llm_backends.cloud.litellm.acompletion", new=fake_acompletion):
        chunks = []
        async for chunk in backend.stream_chat_completion([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

    contents = [
        c["choices"][0]["delta"].get("content")
        for c in chunks
        if c["choices"][0]["delta"].get("content")
    ]
    assert contents == ["ok"]


def test_litellm_globals_set_at_initialize(monkeypatch):
    """litellm global mutations happen in initialize(), not at import time."""
    import zikos.services.llm_backends.cloud as cloud_mod

    monkeypatch.setattr(cloud_mod.litellm, "drop_params", False, raising=False)
    monkeypatch.setattr(cloud_mod.litellm, "suppress_debug_info", False, raising=False)

    b = CloudBackend()
    b.initialize(model_name="gpt-4o")

    assert cloud_mod.litellm.drop_params is True
    assert cloud_mod.litellm.suppress_debug_info is True


# ---------------------------------------------------------------------------
# create_backend factory
# ---------------------------------------------------------------------------


@pytest.fixture
def cloud_provider_env(monkeypatch):
    """Set LLM_PROVIDER and reload config/backends, restoring both afterwards.

    Reloading zikos.config replaces the module-level settings object; without
    the teardown reload, every later test in the session would see the
    cloud-flavored settings (this polluted test_model_strategy in CI).
    """
    import importlib
    import os

    import zikos.config as cfg_mod
    import zikos.services.llm_backends as backends_mod

    def _set(provider: str):
        monkeypatch.setenv("LLM_PROVIDER", provider)
        importlib.reload(cfg_mod)
        importlib.reload(backends_mod)

    yield _set

    os.environ.pop("LLM_PROVIDER", None)
    importlib.reload(cfg_mod)
    importlib.reload(backends_mod)


def test_create_backend_returns_cloud_for_openai_provider(cloud_provider_env):
    cloud_provider_env("openai")

    from zikos.services.llm_backends import create_backend
    from zikos.services.llm_backends.cloud import CloudBackend

    backend = create_backend()
    assert isinstance(backend, CloudBackend)


def test_create_backend_returns_cloud_for_anthropic_provider(cloud_provider_env):
    cloud_provider_env("anthropic")

    from zikos.services.llm_backends import create_backend
    from zikos.services.llm_backends.cloud import CloudBackend

    backend = create_backend()
    assert isinstance(backend, CloudBackend)
