"""Abstract base class for LLM backends"""

from abc import ABC, abstractmethod
from typing import Any


class LLMBackend(ABC):
    """Abstract interface for LLM backends"""

    @abstractmethod
    def initialize(
        self,
        model_path: str,
        n_ctx: int = 32768,
        n_gpu_layers: int = 0,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs: Any,
    ) -> None:
        """Initialize the backend with model and configuration"""
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

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this backend supports native tool calling"""
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
