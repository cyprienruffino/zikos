"""LlamaCpp backend implementation"""

import asyncio
from collections.abc import AsyncGenerator, Iterator
from typing import Any, cast

try:
    from llama_cpp import Llama, llama_state_load_file
except ImportError:
    Llama = None  # type: ignore[assignment,misc]
    llama_state_load_file = None

from zikos.services.llm_backends.base import LLMBackend


class LlamaCppBackend(LLMBackend):
    """Backend using llama-cpp-python for GGUF models"""

    def __init__(self):
        self.llm: Llama | None = None
        self.n_ctx: int = 32768
        self.model_path: str | None = None
        self.system_prompt_cache_path: str | None = None
        self._cached_system_prompt_text: str | None = None

    def initialize(self, **kwargs: Any) -> None:
        """Initialize llama-cpp-python backend.

        Expected kwargs: model_path, n_ctx, n_gpu_layers, temperature, top_p, ...
        Extra kwargs are forwarded to the Llama constructor.
        """
        if Llama is None:
            raise ImportError(
                "llama-cpp-python is not installed. Install with: pip install llama-cpp-python"
            )

        model_path: str = kwargs.pop("model_path")
        n_ctx: int = kwargs.pop("n_ctx", 32768)
        n_gpu_layers: int = kwargs.pop("n_gpu_layers", 0)
        kwargs.pop("temperature", None)
        kwargs.pop("top_p", None)

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

        init_kwargs: dict[str, Any] = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
        }
        init_kwargs.update(kwargs)  # forward remaining Llama-specific kwargs

        if "rope_freq_base" not in init_kwargs:
            init_kwargs["rope_freq_base"] = 0.0
        if "rope_freq_scale" not in init_kwargs:
            init_kwargs["rope_freq_scale"] = 0.0

        import logging
        from pathlib import Path

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

        self._load_system_prompt_cache()

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
        return dict(result)  # type: ignore[arg-type]

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

        # llama-cpp-python's generator is synchronous and blocks the event loop
        # (both on the initial prompt processing and on every token). Run the
        # call + iteration in a worker thread, feeding an asyncio.Queue.
        llm = self.llm
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()
        sentinel = object()

        def _produce() -> None:
            try:
                # stream=True returns an iterator of chunk dicts; narrow past
                # the non-streaming overload mypy also sees.
                chunks = cast(
                    "Iterator[dict[str, Any]]",
                    llm.create_chat_completion(**completion_kwargs),
                )
                for chunk in chunks:
                    loop.call_soon_threadsafe(queue.put_nowait, dict(chunk))
            except BaseException as e:  # propagate to the async consumer
                loop.call_soon_threadsafe(queue.put_nowait, e)
                return
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

        loop.run_in_executor(None, _produce)

        while True:
            item = await queue.get()
            if item is sentinel:
                break
            if isinstance(item, BaseException):
                raise item
            yield item

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

    def _load_system_prompt_cache(self) -> None:
        """Load pre-computed system prompt KV cache if available"""
        import logging
        import os
        from pathlib import Path

        logger = logging.getLogger(__name__)

        if self.llm is None:
            return

        cache_path = os.getenv("SYSTEM_PROMPT_CACHE_PATH")
        if not cache_path:
            if not self.model_path:
                logger.debug("No model path, cannot auto-detect cache")
                return
            cache_file = (
                Path(self.model_path).parent / f"{Path(self.model_path).stem}_system_cache.bin"
            )
            if cache_file.exists():
                cache_path = str(cache_file)
            else:
                logger.debug(
                    "No system prompt cache found, will process system prompt on first request"
                )
                return

        cache_path_obj = Path(cache_path)
        if not cache_path_obj.exists():
            logger.warning(f"System prompt cache file not found: {cache_path}")
            return

        if llama_state_load_file is None:
            logger.warning("llama-cpp-python state loading not available")
            return

        try:
            from ctypes import byref, c_int, c_size_t

            max_tokens = self.n_ctx
            tokens_array = (c_int * max_tokens)()
            n_token_count = c_size_t(0)

            result = llama_state_load_file(
                self.llm.ctx,
                str(cache_path_obj).encode("utf-8"),
                tokens_array,
                max_tokens,
                byref(n_token_count),
            )

            if not result:
                logger.warning(f"Failed to load system prompt cache from {cache_path}")
                return

            logger.info(
                f"Loaded system prompt KV cache from {cache_path} "
                f"({n_token_count.value} tokens cached)"
            )
            self.system_prompt_cache_path = cache_path

            # Load sidecar text file if it exists
            sidecar_path = cache_path_obj.with_suffix(".txt")
            if sidecar_path.exists():
                try:
                    self._cached_system_prompt_text = sidecar_path.read_text(encoding="utf-8")
                    logger.info(
                        f"Loaded cached system prompt text from {sidecar_path} "
                        f"({len(self._cached_system_prompt_text)} chars)"
                    )
                except Exception as e:
                    logger.warning(f"Failed to load sidecar text file: {e}")
        except Exception as e:
            logger.warning(f"Failed to load system prompt cache: {e}")

    def is_initialized(self) -> bool:
        """Check if backend is initialized"""
        return self.llm is not None

    def get_cached_system_prompt(self) -> str | None:
        """Get the cached system prompt text if available"""
        return self._cached_system_prompt_text
