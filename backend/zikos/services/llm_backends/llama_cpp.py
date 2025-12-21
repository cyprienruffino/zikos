"""LlamaCpp backend implementation"""

from typing import Any

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from zikos.services.llm_backends.base import LLMBackend


class LlamaCppBackend(LLMBackend):
    """Backend using llama-cpp-python for GGUF models"""

    def __init__(self):
        self.llm: Llama | None = None
        self.n_ctx: int = 32768

    def initialize(
        self,
        model_path: str,
        n_ctx: int = 32768,
        n_gpu_layers: int = 0,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs: Any,
    ) -> None:
        """Initialize llama-cpp-python backend"""
        if Llama is None:
            raise ImportError(
                "llama-cpp-python is not installed. Install with: pip install llama-cpp-python"
            )

        self.n_ctx = n_ctx
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            **kwargs,
        )

    def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create chat completion using llama-cpp-python"""
        if self.llm is None:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        completion_kwargs: dict[str, Any] = {
            "messages": messages,
            **kwargs,
        }

        if temperature is not None:
            completion_kwargs["temperature"] = temperature
        if top_p is not None:
            completion_kwargs["top_p"] = top_p
        if tools is not None:
            completion_kwargs["tools"] = tools

        result = self.llm.create_chat_completion(**completion_kwargs)
        return dict(result)

    def supports_tools(self) -> bool:
        """LlamaCpp supports tools via create_chat_completion"""
        return True

    def get_context_window(self) -> int:
        """Get configured context window"""
        return self.n_ctx

    def close(self) -> None:
        """Cleanup llama-cpp-python resources"""
        if self.llm is not None:
            try:
                if hasattr(self.llm, "close"):
                    self.llm.close()
            except Exception:
                pass
            self.llm = None

    def is_initialized(self) -> bool:
        """Check if backend is initialized"""
        return self.llm is not None
