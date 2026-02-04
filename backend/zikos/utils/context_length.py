"""Utility to detect model context length from model files"""

import json
import logging
import re
from pathlib import Path

from zikos.utils.gpu import HardwareProfile

_logger = logging.getLogger(__name__)


# KV cache memory per token per layer (bytes) for different quantizations
# These are approximate values for typical model architectures
# Formula: 2 (K+V) * num_heads * head_dim * sizeof(dtype)
# For 32 heads * 128 dim * 2 bytes (fp16) = 8KB per layer per token
KV_CACHE_BYTES_PER_TOKEN_PER_LAYER = {
    "7b": 8192,  # ~8KB per layer
    "8b": 8192,
    "14b": 10240,  # ~10KB per layer (larger hidden dim)
    "32b": 16384,  # ~16KB per layer
    "70b": 16384,
}

# Approximate number of layers for different model sizes
MODEL_LAYERS = {
    "0.6b": 28,
    "1.7b": 28,
    "4b": 36,
    "7b": 32,
    "8b": 32,
    "14b": 40,
    "32b": 64,
    "70b": 80,
}


def parse_model_size(model_path: str) -> str | None:
    """Extract model size (e.g., '7b', '14b') from model path/filename"""
    model_lower = model_path.lower()
    # Match patterns like "7b", "14b", "0.6b", "1.7b"
    match = re.search(r"(\d+\.?\d*b)", model_lower)
    if match:
        return match.group(1)
    return None


def estimate_model_base_memory_gb(model_path: str) -> float:
    """Estimate base model memory from file size or model size indicator"""
    path = Path(model_path)

    # If file exists, use actual file size as base memory estimate
    # GGUF files are loaded mostly into memory (with some overhead)
    if path.exists() and path.is_file():
        file_size_gb = path.stat().st_size / (1024**3)
        # Add ~20% overhead for model loading
        return file_size_gb * 1.2

    # Fallback: estimate from model size in name
    model_size = parse_model_size(model_path)
    if model_size:
        # Rough Q4 quantization sizes
        size_estimates = {
            "0.6b": 0.5,
            "1.7b": 1.2,
            "4b": 2.8,
            "7b": 4.5,
            "8b": 5.0,
            "14b": 9.0,
            "32b": 20.0,
            "70b": 40.0,
        }
        return size_estimates.get(model_size, 5.0) * 1.2

    # Default fallback
    return 5.0


def estimate_kv_cache_memory_gb(model_path: str, context_length: int) -> float:
    """Estimate KV cache memory for a given context length"""
    model_size = parse_model_size(model_path)

    if model_size:
        # Get bytes per token per layer
        bytes_per_token_layer = KV_CACHE_BYTES_PER_TOKEN_PER_LAYER.get(model_size, 8192)
        num_layers = MODEL_LAYERS.get(model_size, 32)
    else:
        # Conservative defaults
        bytes_per_token_layer = 8192
        num_layers = 32

    total_bytes = bytes_per_token_layer * num_layers * context_length
    return total_bytes / (1024**3)


def estimate_max_context_for_memory(
    model_path: str,
    available_memory_gb: float,
    native_context_length: int | None = None,
) -> int:
    """Estimate maximum viable context length for available memory

    Args:
        model_path: Path to the model file
        available_memory_gb: Available GPU VRAM or system RAM in GB
        native_context_length: Model's native context limit (if known)

    Returns:
        Recommended maximum context length
    """
    # Reserve some memory for compute/overhead
    usable_memory = available_memory_gb * 0.85

    # Subtract base model memory
    base_memory = estimate_model_base_memory_gb(model_path)
    memory_for_kv = usable_memory - base_memory

    if memory_for_kv <= 0:
        _logger.warning(
            f"Model base memory ({base_memory:.1f}GB) exceeds available memory "
            f"({available_memory_gb:.1f}GB). Using minimum context."
        )
        return 2048  # Minimum viable context

    # Calculate max context that fits
    model_size = parse_model_size(model_path)
    if model_size:
        bytes_per_token_layer = KV_CACHE_BYTES_PER_TOKEN_PER_LAYER.get(model_size, 8192)
        num_layers = MODEL_LAYERS.get(model_size, 32)
    else:
        bytes_per_token_layer = 8192
        num_layers = 32

    bytes_per_token = bytes_per_token_layer * num_layers
    max_context = int((memory_for_kv * 1024**3) / bytes_per_token)

    # Round down to nearest 1024 for cleaner numbers
    max_context = (max_context // 1024) * 1024
    max_context = max(max_context, 2048)  # Minimum viable

    # Cap at native context length if known
    if native_context_length:
        max_context = min(max_context, native_context_length)

    _logger.info(
        f"Estimated max context: {max_context} tokens "
        f"(base model: {base_memory:.1f}GB, KV cache budget: {memory_for_kv:.1f}GB)"
    )

    return max_context


def get_recommended_context_length(
    model_path: str,
    hardware: HardwareProfile,
    native_context_length: int | None = None,
) -> int:
    """Get recommended context length based on hardware and model

    Args:
        model_path: Path to the model file
        hardware: Hardware profile with GPU/RAM info
        native_context_length: Model's native context limit (if known)

    Returns:
        Recommended context length
    """
    # Determine available memory based on whether we'll use GPU or CPU
    if hardware.gpu.available and hardware.gpu.memory_free_gb:
        available_memory = hardware.gpu.memory_free_gb
        _logger.info(f"Using GPU memory: {available_memory:.1f}GB available")
    else:
        available_memory = hardware.ram.available_gb
        _logger.info(f"Using system RAM: {available_memory:.1f}GB available")

    return estimate_max_context_for_memory(model_path, available_memory, native_context_length)


def detect_context_length(model_path: str, backend_type: str | None = None) -> int:
    """Detect the native context length of a model from its metadata

    Args:
        model_path: Path to the model file (GGUF) or directory (Transformers)
        backend_type: Optional backend type hint ('llama_cpp' or 'transformers')

    Returns:
        The detected context length in tokens

    Raises:
        RuntimeError: If context length cannot be detected from the model
    """
    model_path_obj = Path(model_path)
    model_path_lower = str(model_path).lower()

    # Determine backend type if not provided
    if backend_type is None:
        if model_path_lower.endswith(".gguf"):
            backend_type = "llama_cpp"
        elif model_path_obj.exists() and model_path_obj.is_dir():
            backend_type = "transformers"
        elif any(x in model_path_lower for x in ["qwen3", "qwen/qwen3"]):
            backend_type = "transformers"
        elif "/" in model_path and not model_path_lower.endswith(".gguf"):
            backend_type = "transformers"
        else:
            backend_type = "llama_cpp"

    if backend_type in ("llama_cpp", "llama-cpp", "gguf"):
        return _detect_gguf_context_length(model_path)
    else:
        return _detect_transformers_context_length(model_path)


def _detect_gguf_context_length(model_path: str) -> int:
    """Detect context length from GGUF model metadata"""
    try:
        from llama_cpp import Llama

        model = None
        try:
            # Initialize with minimal n_ctx to read metadata
            # Use n_ctx=1 to minimize memory usage
            model = Llama(model_path=model_path, n_ctx=1, verbose=False, n_threads=1)

            # First, try to read from model metadata (most reliable)
            if hasattr(model, "_model"):
                try:
                    from llama_cpp import (
                        llama_model_meta_key_by_index,
                        llama_model_meta_val_str_by_index,
                    )

                    # Try to get metadata count
                    metadata_count = 0
                    if hasattr(model._model, "metadata_kv_count"):
                        metadata_count = model._model.metadata_kv_count()
                    else:
                        # Try iterating until we get an error
                        metadata_count = 100  # Reasonable upper bound

                    # Search for context length in metadata
                    for i in range(metadata_count):
                        try:
                            key = llama_model_meta_key_by_index(model._model, i)
                            val = llama_model_meta_val_str_by_index(model._model, i)

                            if key in (
                                "llama.context_length",
                                "general.context_length",
                                "context_length",
                            ):
                                context_length = int(val)
                                if context_length > 0:
                                    _logger.info(
                                        f"Detected GGUF context length from metadata: {context_length} tokens"
                                    )
                                    return context_length
                        except (IndexError, ValueError, TypeError):
                            break
                except ImportError:
                    # Metadata functions not available in this version
                    pass
                except Exception as e:
                    _logger.debug(f"Could not read metadata: {e}")

            # Fallback: Try to get from model's internal parameters
            # Some models expose context_length as an attribute
            if hasattr(model, "context_length"):
                context_length = model.context_length
                if context_length and context_length > 0:
                    _logger.info(
                        f"Detected GGUF context length from model attribute: {context_length} tokens"
                    )
                    return int(context_length)

            # Last resort: Check model's n_ctx_train or similar
            # Note: n_ctx() returns what we passed in, not the model's limit
            # But we can check if there's a training context length
            if hasattr(model, "_model"):
                try:
                    # Try to access model params directly
                    if hasattr(model._model, "n_ctx_train"):
                        context_length = model._model.n_ctx_train()
                        if context_length and context_length > 0:
                            _logger.info(
                                f"Detected GGUF context length from n_ctx_train: {context_length} tokens"
                            )
                            return context_length
                except Exception:
                    pass

        except ImportError as err:
            raise RuntimeError(
                "llama-cpp-python is not installed. Cannot detect context length for GGUF models."
            ) from err
        finally:
            # Clean up
            if model is not None:
                try:
                    model.close()
                except Exception:
                    pass

        raise RuntimeError(
            f"Could not detect context length from GGUF model at {model_path}. "
            "The model may be corrupted or in an unsupported format. "
            "Please set LLM_N_CTX environment variable manually."
        )

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Error detecting context length from GGUF model {model_path}: {e}"
        ) from e


def _detect_transformers_context_length(model_path: str) -> int:
    """Detect context length from Transformers model config.json"""
    model_path_obj = Path(model_path)

    # If it's a HuggingFace model ID, we'd need to download config
    # For now, assume it's a local path
    if not model_path_obj.exists():
        # Try to load from HuggingFace (would require transformers library)
        # For now, raise error
        raise RuntimeError(
            f"Model path does not exist: {model_path}. "
            "Cannot detect context length for remote HuggingFace models automatically."
        )

    if model_path_obj.is_file():
        # If it's a file, try parent directory
        config_path = model_path_obj.parent / "config.json"
    else:
        # It's a directory
        config_path = model_path_obj / "config.json"

    if not config_path.exists():
        raise RuntimeError(
            f"Could not find config.json at {config_path}. "
            "Cannot detect context length for Transformers model."
        )

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Try common keys for context length
        context_length = None

        # Most common: max_position_embeddings
        if "max_position_embeddings" in config:
            context_length = int(config["max_position_embeddings"])
        # Alternative: n_positions
        elif "n_positions" in config:
            context_length = int(config["n_positions"])
        # Some models use: max_seq_length
        elif "max_seq_length" in config:
            context_length = int(config["max_seq_length"])

        if context_length is not None:
            _logger.info(f"Detected Transformers context length: {context_length} tokens")
            return context_length

        raise RuntimeError(
            f"Could not find context length in config.json at {config_path}. "
            "Expected one of: max_position_embeddings, n_positions, max_seq_length"
        )

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in config.json at {config_path}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error reading config.json from {config_path}: {e}") from e
