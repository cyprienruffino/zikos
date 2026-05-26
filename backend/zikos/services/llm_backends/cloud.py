"""Cloud LLM backend using litellm (OpenAI, Anthropic, Gemini, Mistral, ...)"""

from collections.abc import AsyncGenerator
from typing import Any

try:
    import litellm

    litellm.drop_params = True  # ignore unsupported params per-provider silently
except ImportError:
    litellm = None  # type: ignore[assignment]

from zikos.services.llm_backends.base import LLMBackend


class CloudBackend(LLMBackend):
    """Backend for cloud-hosted LLMs via litellm.

    Supports any provider litellm supports: OpenAI, Anthropic, Gemini, Mistral, etc.
    Model names follow litellm conventions, e.g.:
        gpt-4o
        claude-opus-4-7  (or anthropic/claude-opus-4-7)
        gemini/gemini-2.0-flash
        mistral/mistral-large-latest
    """

    def __init__(self):
        self._model: str = ""
        self._api_key: str | None = None
        self._temperature: float = 0.7
        self._top_p: float = 0.9
        self._initialized: bool = False

    def initialize(self, **kwargs: Any) -> None:
        """Initialize the cloud backend.

        Expected kwargs: model_name (required), api_key, temperature, top_p
        """
        if litellm is None:
            raise ImportError("litellm is not installed. Install with: pip install litellm")

        self._model = kwargs["model_name"]
        self._api_key = kwargs.get("api_key") or None
        self._temperature = kwargs.get("temperature", 0.7)
        self._top_p = kwargs.get("top_p", 0.9)
        self._initialized = True

    def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self._initialized:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        completion_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._temperature,
            "top_p": top_p if top_p is not None else self._top_p,
        }
        if tools:
            completion_kwargs["tools"] = tools
        if self._api_key:
            completion_kwargs["api_key"] = self._api_key

        try:
            response = litellm.completion(**completion_kwargs)
        except litellm.BadRequestError as e:
            if "temperature" in str(e).lower():
                completion_kwargs.pop("temperature", None)
                completion_kwargs.pop("top_p", None)
                response = litellm.completion(**completion_kwargs)
            else:
                raise
        return response.model_dump()  # type: ignore[no-any-return]

    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        if not self._initialized:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        completion_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "temperature": temperature if temperature is not None else self._temperature,
            "top_p": top_p if top_p is not None else self._top_p,
        }
        if tools:
            completion_kwargs["tools"] = tools
        if self._api_key:
            completion_kwargs["api_key"] = self._api_key

        try:
            response = await litellm.acompletion(**completion_kwargs)
        except litellm.BadRequestError as e:
            if "temperature" in str(e).lower():
                completion_kwargs.pop("temperature", None)
                completion_kwargs.pop("top_p", None)
                response = await litellm.acompletion(**completion_kwargs)
            else:
                raise

        # Accumulate tool_call deltas so the final chunk carries complete tool calls,
        # matching what stream_processor and NativeToolCallParser expect.
        tool_call_accumulator: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            chunk_dict = chunk.model_dump()
            choice = chunk_dict.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            finish_reason = choice.get("finish_reason")

            if delta.get("content"):
                yield {
                    "choices": [
                        {
                            "delta": {"content": delta["content"], "role": "assistant"},
                            "finish_reason": None,
                        }
                    ]
                }

            for tc_delta in delta.get("tool_calls") or []:
                idx = tc_delta.get("index", 0)
                if idx not in tool_call_accumulator:
                    tool_call_accumulator[idx] = {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                tc = tool_call_accumulator[idx]
                if tc_delta.get("id"):
                    tc["id"] = tc_delta["id"]
                fn = tc_delta.get("function") or {}
                if fn.get("name"):
                    tc["function"]["name"] += fn["name"]
                if fn.get("arguments"):
                    tc["function"]["arguments"] += fn["arguments"]

            if finish_reason:
                final_choice: dict[str, Any] = {"delta": {}, "finish_reason": finish_reason}
                if tool_call_accumulator:
                    tool_calls = list(tool_call_accumulator.values())
                    final_choice["delta"]["tool_calls"] = tool_calls
                    final_choice["tool_calls"] = tool_calls
                yield {"choices": [final_choice]}
                break

    def supports_tools(self) -> bool:
        return True

    def supports_system_messages(self) -> bool:
        return True

    def get_context_window(self) -> int:
        try:
            info = litellm.get_model_info(self._model)
            return int(info.get("max_input_tokens") or info.get("max_tokens") or 128000)
        except Exception:
            return 128000

    def close(self) -> None:
        pass

    def is_initialized(self) -> bool:
        return self._initialized
