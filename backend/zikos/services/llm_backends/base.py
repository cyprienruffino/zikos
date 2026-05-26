"""Abstract base class for LLM backends"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any


class LLMBackend(ABC):
    """Abstract interface for LLM backends"""

    @abstractmethod
    def initialize(self, **kwargs: Any) -> None:
        """Initialize the backend with model and configuration.

        Local backends expect: model_path, n_ctx, n_gpu_layers, temperature, top_p, ...
        Cloud backend expects: model_name, api_key, temperature, top_p
        """
        pass

    @abstractmethod
    def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a chat completion

        Returns standardized format:
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "...",
                    "tool_calls": [...] (optional)
                },
                "finish_reason": "..."
            }]
        }
        """
        pass

    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion tokens

        Yields standardized format chunks:
        {
            "choices": [{
                "delta": {
                    "content": "token",
                    "role": "assistant",
                    "tool_calls": [...] (optional, only in final chunk)
                },
                "finish_reason": None | "stop" | "tool_calls" | ...
            }]
        }

        Default implementation falls back to non-streaming and yields final result.
        Backends should override this for true streaming.
        """
        result = self.create_chat_completion(
            messages=messages,
            tools=tools,
            temperature=temperature,
            top_p=top_p,
            **kwargs,
        )

        # Simulate streaming by yielding the full response as a single chunk
        content = result["choices"][0]["message"].get("content", "")
        if content:
            # Split content into words for simulation
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

        # Final chunk with finish reason
        yield {
            "choices": [
                {
                    "delta": {},
                    "finish_reason": result["choices"][0].get("finish_reason", "stop"),
                }
            ]
        }

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this backend supports native tool calling"""
        pass

    @abstractmethod
    def supports_system_messages(self) -> bool:
        """Whether this backend properly handles system messages

        All supported models (Phi-3, Qwen, Llama 3.x, Mistral) support system messages natively.

        Returns:
            True if system messages should be kept separate (always True for supported models)
        """
        pass

    @abstractmethod
    def get_context_window(self) -> int:
        """Get the configured context window size"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleanup resources"""
        pass

    def is_initialized(self) -> bool:
        """Check if backend is initialized"""
        return False

    def get_cached_system_prompt(self) -> str | None:
        """Get the cached system prompt text if a KV cache was loaded

        Returns:
            The full system prompt text if a cache with sidecar text was loaded,
            None otherwise.
        """
        return None
