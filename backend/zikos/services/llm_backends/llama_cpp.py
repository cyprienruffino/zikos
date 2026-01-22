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
        self.model_path: str | None = None

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
        self.model_path = model_path

        init_kwargs = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
        }

        init_kwargs.update(kwargs)

        if "rope_freq_base" not in init_kwargs:
            init_kwargs["rope_freq_base"] = 0.0
        if "rope_freq_scale" not in init_kwargs:
            init_kwargs["rope_freq_scale"] = 0.0

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Initializing Llama with: {init_kwargs}")

        self.llm = Llama(**init_kwargs)

        try:
            if hasattr(self.llm, "n_ctx"):
                actual_ctx = self.llm.n_ctx()
                if actual_ctx < n_ctx:
                    logger.warning(
                        f"Model context window ({actual_ctx}) is smaller than requested ({n_ctx}). "
                        f"Using model's limit to prevent garbled output."
                    )
                    self.n_ctx = actual_ctx

                    if hasattr(self.llm, "ctx_params"):
                        self.llm.ctx_params.n_ctx = actual_ctx
        except Exception as e:
            logger.warning(f"Could not verify model context window: {e}")

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

        import logging

        logger = logging.getLogger(__name__)

        logger.debug(f"Streaming with kwargs: {completion_kwargs}")
        logger.debug(f"Messages being sent: {messages}")

        stream = self.llm.create_chat_completion(**completion_kwargs)

        for chunk in stream:
            chunk_dict = dict(chunk)
            logger.debug(f"Received chunk: {chunk_dict}")

            yield chunk_dict

    def supports_tools(self) -> bool:
        """LlamaCpp supports tools via create_chat_completion"""
        return True

    def supports_system_messages(self) -> bool:
        """All supported models support system messages natively

        Supported models (Phi-3, Qwen2.5, Llama 3.x, Mistral) all support
        system messages through llama-cpp-python's create_chat_completion.
        """
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
