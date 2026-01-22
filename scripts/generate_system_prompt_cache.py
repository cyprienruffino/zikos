#!/usr/bin/env python3
"""Generate and save system prompt KV cache for faster server startup

This script pre-computes the KV cache for the system prompt, which can be
loaded on server startup to avoid reprocessing it for every conversation.

Usage:
    python scripts/generate_system_prompt_cache.py [--model-path PATH] [--output PATH]

The cache file can be generated in CI and included in deployments.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from zikos.config import settings  # noqa: E402
from zikos.services.llm import LLMService  # noqa: E402

try:
    from llama_cpp import Llama, llama_state_save_file  # noqa: E402
except ImportError:
    print("Error: llama-cpp-python is not installed")
    sys.exit(1)


def generate_cache(
    model_path: str | None = None,
    output_path: str | None = None,
    n_ctx: int = 32768,
    n_gpu_layers: int = 0,
) -> Path:
    """Generate system prompt KV cache

    Args:
        model_path: Path to model file. If None, uses LLM_MODEL_PATH from settings.
        output_path: Path to save cache file. If None, saves to models/ directory.
        n_ctx: Context window size
        n_gpu_layers: Number of GPU layers

    Returns:
        Path to the generated cache file
    """
    if model_path is None:
        model_path = settings.llm_model_path
        if not model_path:
            raise ValueError("Model path not specified. Set LLM_MODEL_PATH or use --model-path")

    model_path_obj = Path(model_path)
    if not model_path_obj.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    print(f"Loading model from {model_path}...")
    llm = Llama(
        model_path=str(model_path),
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        verbose=False,
    )

    print("Getting system prompt...")
    service = LLMService()
    system_prompt = service._get_system_prompt()
    print(f"System prompt length: {len(system_prompt)} characters")

    print("Formatting system message for chat...")
    system_message = [{"role": "system", "content": system_prompt}]

    print("Processing system prompt to build KV cache...")
    chat_handler = llm.chat_handler
    if chat_handler:
        formatted = chat_handler.apply_chat_template(system_message, tokenize=False)
        tokens = llm.tokenize(formatted.encode("utf-8"), add_bos=True)
        print(f"Tokenized system prompt: {len(tokens)} tokens")
        llm.eval(tokens)
    else:
        print("Warning: No chat handler, using create_chat_completion fallback...")
        result = llm.create_chat_completion(
            messages=system_message,
            max_tokens=1,
            temperature=0.0,
        )

    print("Saving KV cache state...")
    state = llm.save_state()
    print(f"Cached {state.n_tokens} tokens")

    if output_path is None:
        cache_file = model_path_obj.parent / f"{model_path_obj.stem}_system_cache.bin"
    else:
        cache_file = Path(output_path)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    from ctypes import POINTER, c_int, cast

    import numpy as np

    tokens_list = (
        state.input_ids.tolist() if hasattr(state.input_ids, "tolist") else list(state.input_ids)
    )
    tokens_array = (c_int * len(tokens_list))(*tokens_list)
    result = llama_state_save_file(
        llm.ctx,
        str(cache_file).encode("utf-8"),
        tokens_array,
        len(tokens_list),
    )
    if not result:
        raise RuntimeError("Failed to save state to file")

    file_size_kb = cache_file.stat().st_size / 1024
    print(f"✓ Saved KV cache to {cache_file}")
    print(f"  Cache file size: {file_size_kb:.2f} KB")
    print(f"  Cached tokens: {state.n_tokens}")

    return cache_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate system prompt KV cache for faster server startup"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        help="Path to model file (default: from LLM_MODEL_PATH env var)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output cache file path (default: models/{model_name}_system_cache.bin)",
    )
    parser.add_argument(
        "--n-ctx",
        type=int,
        default=32768,
        help="Context window size (default: 32768)",
    )
    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=0,
        help="Number of GPU layers (default: 0, CPU only)",
    )

    args = parser.parse_args()

    try:
        cache_file = generate_cache(
            model_path=args.model_path,
            output_path=args.output,
            n_ctx=args.n_ctx,
            n_gpu_layers=args.n_gpu_layers,
        )
        print(f"\n✓ Success! Cache file ready: {cache_file}")
        print("\nTo use this cache, set SYSTEM_PROMPT_CACHE_PATH environment variable")
        print(f"  export SYSTEM_PROMPT_CACHE_PATH={cache_file}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
