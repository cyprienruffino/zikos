"""Fake LLM backend for testing."""

from collections.abc import AsyncGenerator
from typing import Any

from zikos.services.llm_backends.base import LLMBackend


class FakeBackend(LLMBackend):
    """Deterministic LLM backend for tests.

    Usage:
        # Simple text response
        backend = FakeBackend("Here is my analysis of your performance.")

        # Response with tool calls
        backend = FakeBackend(tool_calls=[{
            "id": "call_1",
            "function": {"name": "analyze_tempo", "arguments": '{"audio_file_id": "test.wav"}'},
        }])

        # Sequence of responses (for multi-turn tool call flows)
        backend = FakeBackend(responses=[
            "First response",
            "Second response after tool result",
        ])
    """

    def __init__(
        self,
        response: str = "Test response",
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        responses: list[str | dict[str, Any]] | None = None,
        context_window: int = 4096,
    ):
        self._default_response = response
        self._default_tool_calls = tool_calls
        self._responses = list(responses) if responses else None
        self._call_index = 0
        self._context_window = context_window
        self._initialized = False
        self._messages_received: list[list[dict[str, Any]]] = []

    def initialize(self, model_path: str, n_ctx: int = 32768, n_gpu_layers: int = 0, **kwargs):
        self._initialized = True
        self._context_window = n_ctx

    def create_chat_completion(self, messages: list[dict[str, Any]], **kwargs) -> dict[str, Any]:
        self._messages_received.append(messages)

        response_content = self._default_response
        tool_calls = self._default_tool_calls
        finish_reason = "stop"

        if self._responses and self._call_index < len(self._responses):
            entry = self._responses[self._call_index]
            self._call_index += 1
            if isinstance(entry, dict):
                response_content = entry.get("content", "")
                tool_calls = entry.get("tool_calls")
            else:
                response_content = entry

        message: dict[str, Any] = {"role": "assistant", "content": response_content}
        if tool_calls:
            message["tool_calls"] = tool_calls
            finish_reason = "tool_calls"

        return {"choices": [{"message": message, "finish_reason": finish_reason}]}

    async def stream_chat_completion(
        self, messages, **kwargs
    ) -> AsyncGenerator[dict[str, Any], None]:
        result = self.create_chat_completion(messages, **kwargs)
        message = result["choices"][0]["message"]
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")
        finish_reason = result["choices"][0].get("finish_reason", "stop")

        if content:
            words = content.split()
            for i, word in enumerate(words):
                yield {
                    "choices": [
                        {
                            "delta": {
                                "content": word + (" " if i < len(words) - 1 else ""),
                                "role": "assistant",
                            },
                            "finish_reason": None,
                        }
                    ]
                }

        final_choice: dict[str, Any] = {"delta": {}, "finish_reason": finish_reason}
        if tool_calls:
            final_choice["delta"]["tool_calls"] = tool_calls
            final_choice["tool_calls"] = tool_calls
        yield {"choices": [final_choice]}

    def supports_tools(self) -> bool:
        return False

    def supports_system_messages(self) -> bool:
        return True

    def get_context_window(self) -> int:
        return self._context_window

    def close(self) -> None:
        pass

    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def messages_received(self) -> list[list[dict[str, Any]]]:
        """Access messages sent to the backend for assertions."""
        return self._messages_received
