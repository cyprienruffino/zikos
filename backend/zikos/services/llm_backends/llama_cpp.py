"""LlamaCpp backend implementation"""

from collections.abc import AsyncGenerator
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

        cuda_available = False
        if n_gpu_layers != 0:
            try:
                from llama_cpp import llama_cpp

                if hasattr(llama_cpp, "llama_supports_gpu_offload"):
                    cuda_available = llama_cpp.llama_supports_gpu_offload()
                elif hasattr(llama_cpp, "ggml_cuda_available"):
                    cuda_available = llama_cpp.ggml_cuda_available()
            except Exception:
                pass

            if not cuda_available:
                print(
                    "WARNING: llama-cpp-python was installed without CUDA support. "
                    "GPU acceleration will not be available."
                )
                print(
                    "To enable GPU support, reinstall llama-cpp-python with CUDA:\n"
                    "  pip uninstall llama-cpp-python\n"
                    "  pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121\n"
                    "  (or cu118, cu124 depending on your CUDA version)"
                )
                print("Falling back to CPU (n_gpu_layers will be ignored)")
                n_gpu_layers = 0
            else:
                print("CUDA support detected in llama-cpp-python")
                if n_gpu_layers == -1:
                    print("Using full GPU offload (all layers on GPU)")
                else:
                    print(f"Using {n_gpu_layers} GPU layers")

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

    async def stream_chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream chat completion using llama-cpp-python"""
        if self.llm is None:
            raise RuntimeError("Backend not initialized. Call initialize() first.")

        completion_kwargs: dict[str, Any] = {
            "messages": messages,
            "stream": True,
            **kwargs,
        }

        if temperature is not None:
            completion_kwargs["temperature"] = temperature
        if top_p is not None:
            completion_kwargs["top_p"] = top_p
        if tools is not None:
            completion_kwargs["tools"] = tools

        stream = self.llm.create_chat_completion(**completion_kwargs)

        for chunk in stream:
            chunk_dict = dict(chunk)

            choice = chunk_dict.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "")

            if content and isinstance(content, str):
                printable_ratio = sum(1 for c in content if c.isprintable() or c.isspace()) / len(
                    content
                )
                if printable_ratio < 0.5:
                    import logging

                    logging.warning(
                        f"Detected potentially garbled content from llama-cpp: "
                        f"{repr(content[:100])}"
                    )

            yield chunk_dict

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
