"""LLM backend implementations"""

from zikos.services.llm_backends.base import LLMBackend
from zikos.services.llm_backends.llama_cpp import LlamaCppBackend
from zikos.services.llm_backends.transformers import TransformersBackend

__all__ = ["LLMBackend", "LlamaCppBackend", "TransformersBackend", "create_backend"]


def create_backend(
    model_path: str | None = None, backend_type: str | None = None
) -> LLMBackend | None:
    """Create appropriate LLM backend based on model path or explicit type"""
    from zikos.config import settings

    if not model_path:
        model_path = settings.llm_model_path

    if not model_path:
        return None

    if backend_type:
        backend_type = backend_type.lower()
        if backend_type in ["llama_cpp", "llama-cpp", "gguf"]:
            return LlamaCppBackend()
        elif backend_type in ["transformers", "hf", "huggingface"]:
            return TransformersBackend()
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

    from pathlib import Path

    model_path_obj = Path(model_path)
    model_path_lower = str(model_path).lower()

    if model_path_lower.endswith(".gguf"):
        return LlamaCppBackend()
    elif model_path_obj.exists() and model_path_obj.is_dir():
        return TransformersBackend()
    elif any(x in model_path_lower for x in ["qwen3", "qwen/qwen3"]):
        return TransformersBackend()
    elif "/" in model_path and not model_path_lower.endswith(".gguf"):
        return TransformersBackend()
    else:
        return LlamaCppBackend()
