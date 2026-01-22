#!/usr/bin/env python3
"""Run the application"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

import uvicorn  # noqa: E402

from zikos.config import settings  # noqa: E402


def _ensure_system_prompt_cache():
    """Auto-generate system prompt cache if SYSTEM_PROMPT_CACHE_PATH is set but file doesn't exist"""
    cache_path = os.getenv("SYSTEM_PROMPT_CACHE_PATH")
    if not cache_path:
        return

    cache_file = Path(cache_path)
    if cache_file.exists():
        return

    if not settings.llm_model_path:
        print(
            "Warning: SYSTEM_PROMPT_CACHE_PATH is set but LLM_MODEL_PATH is not set. "
            "Cannot auto-generate cache."
        )
        return

    print(f"System prompt cache not found at {cache_path}, generating...")
    print("This may take a few minutes on CPU...")

    try:
        script_path = Path(__file__).parent / "scripts" / "generate_system_prompt_cache.py"
        if not script_path.exists():
            print(f"Warning: Cache generation script not found at {script_path}")
            return

        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--model-path",
                settings.llm_model_path,
                "--output",
                cache_path,
                "--n-ctx",
                str(settings.llm_n_ctx or 32768),
                "--n-gpu-layers",
                str(settings.llm_n_gpu_layers),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print(f"✓ System prompt cache generated: {cache_path}")
        else:
            print("Warning: Failed to auto-generate system prompt cache:")
            print(result.stderr)
            print(
                "Server will start without cache (system prompt will be processed on each request)"
            )
    except Exception as e:
        print(f"Warning: Failed to auto-generate system prompt cache: {e}")
        print("Server will start without cache (system prompt will be processed on each request)")


if __name__ == "__main__":
    _ensure_system_prompt_cache()

    uvicorn.run(
        "zikos.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
