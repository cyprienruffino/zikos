"""LLM backend initialization with automatic context sizing and OOM retry"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zikos.config import settings
from zikos.services.llm_backends import create_backend
from zikos.services.llm_orchestration.tool_call_parser import ToolCallParser, get_tool_call_parser
from zikos.services.model_strategy import ModelStrategy, get_model_strategy
from zikos.utils.context_length import detect_context_length, get_recommended_context_length
from zikos.utils.gpu import detect_hardware, get_optimal_gpu_layers

_logger = logging.getLogger("zikos.services.llm_init")


@dataclass
class LLMInitResult:
    """Result of LLM backend initialization"""

    backend: Any = None
    strategy: ModelStrategy | None = None
    tool_call_parser: ToolCallParser | None = None
    context_window: int | None = None
    error: str | None = None


def initialize_llm_backend() -> LLMInitResult:
    """Initialize LLM backend with automatic context length sizing and OOM retry.

    Returns an LLMInitResult with the backend, strategy, and context window on success,
    or just an error message on failure. The application can start either way.
    """
    result = LLMInitResult()

    if not settings.llm_model_path:
        result.error = "LLM_MODEL_PATH is not set in environment variables"
        return result

    model_path_str = settings.llm_model_path
    model_path = Path(model_path_str)

    if (
        not model_path.exists()
        and not model_path_str.startswith("Qwen/")
        and "/" not in model_path_str
    ):
        result.error = f"Model file not found at {model_path.resolve()}"
        _logger.warning(result.error)
        _logger.warning("The application will start but LLM features will be unavailable.")
        _logger.info(
            f"To download a model, run: python scripts/download_model.py qwen2.5-7b-instruct-q4 -o {model_path.parent}"
        )
        return result

    try:
        backend_type = settings.llm_backend if settings.llm_backend != "auto" else None
        backend = create_backend(model_path_str, backend_type)

        if backend is None:
            result.error = "Could not create LLM backend"
            _logger.warning(result.error)
            return result

        n_ctx = _determine_context_length(model_path_str, backend_type)
        n_gpu_layers = _determine_gpu_layers(model_path_str, backend_type)

        _logger.info(f"Initializing LLM backend: {type(backend).__name__}")
        _logger.info(f"Model path: {model_path_str}")
        _logger.info(f"GPU layers: {n_gpu_layers}")

        backend = _initialize_with_oom_retry(
            backend, model_path_str, backend_type, n_ctx, n_gpu_layers
        )

        result.backend = backend
        result.strategy = get_model_strategy(model_path_str)
        result.tool_call_parser = result.strategy.tool_call_parser
        result.context_window = backend.get_context_window()

        _logger.info(
            f"LLM initialized successfully with context window: {result.context_window} tokens"
        )
        _logger.info(f"Using model strategy: {type(result.strategy.tool_provider).__name__}")

    except Exception as e:
        result.error = str(e)
        _logger.error(f"Error initializing LLM: {e}", exc_info=True)
        _logger.warning("The application will start but LLM features will be unavailable.")
        result.strategy = get_model_strategy()

    return result


def _determine_context_length(model_path_str: str, backend_type: str | None) -> int:
    """Determine optimal context length based on settings, model, and hardware."""
    n_ctx: int | None = settings.llm_n_ctx
    if n_ctx is not None:
        return n_ctx

    native_ctx = None
    try:
        native_ctx = detect_context_length(model_path_str, backend_type)
        _logger.info(f"Auto-detected native context length: {native_ctx} tokens")
    except Exception as e:
        _logger.warning(f"Could not detect native context length: {e}")
        native_ctx = 32768

    hardware = detect_hardware()
    n_ctx = int(get_recommended_context_length(model_path_str, hardware, native_ctx))
    _logger.info(f"Recommended context length for available memory: {n_ctx} tokens")
    return n_ctx


def _determine_gpu_layers(model_path_str: str, backend_type: str | None) -> int:
    """Determine optimal GPU layer count."""
    n_gpu_layers: int = settings.llm_n_gpu_layers
    if n_gpu_layers == -1:
        n_gpu_layers = int(get_optimal_gpu_layers(model_path_str, backend_type or "auto"))
    return n_gpu_layers


def _initialize_with_oom_retry(
    backend, model_path_str: str, backend_type: str | None, n_ctx: int, n_gpu_layers: int
):
    """Try to initialize the backend, retrying with smaller context on OOM."""
    max_retries = 3
    min_ctx = 2048
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            _logger.info(f"Attempting initialization with n_ctx={n_ctx} (attempt {attempt + 1})")
            backend.initialize(
                model_path=model_path_str,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )
            return backend
        except (MemoryError, RuntimeError, OSError) as e:
            error_str = str(e).lower()
            is_oom = (
                isinstance(e, MemoryError)
                or "out of memory" in error_str
                or "cuda" in error_str
                and "memory" in error_str
                or "failed to allocate" in error_str
                or "oom" in error_str
            )

            if is_oom and attempt < max_retries and n_ctx > min_ctx:
                last_error = e
                new_ctx = max(n_ctx // 2, min_ctx)
                _logger.warning(f"OOM error with n_ctx={n_ctx}, retrying with n_ctx={new_ctx}")
                n_ctx = new_ctx
                try:
                    backend.close()
                except Exception:
                    _logger.debug("Error closing backend during OOM retry", exc_info=True)
                backend = create_backend(model_path_str, backend_type)
                continue
            else:
                raise

    raise last_error or RuntimeError("Failed to initialize after retries")
