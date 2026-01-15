#!/usr/bin/env python3
"""Helper script to download Llama models in GGUF format"""

import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download

    HAS_HF_HUB = True
except ImportError:
    HAS_HF_HUB = False


MODEL_CONFIGS = {
    "qwen2.5-7b-instruct-q4": {
        "repo_id": "bartowski/Qwen2.5-7B-Instruct-GGUF",
        "filename": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "description": "Qwen2.5 7B Instruct Q4_K_M (EXCELLENT function calling, recommended)",
        "function_calling": "excellent",
    },
    "qwen2.5-7b-instruct-q5": {
        "repo_id": "bartowski/Qwen2.5-7B-Instruct-GGUF",
        "filename": "Qwen2.5-7B-Instruct-Q5_K_M.gguf",
        "description": "Qwen2.5 7B Instruct Q5_K_M (EXCELLENT function calling, higher quality)",
        "function_calling": "excellent",
    },
    "qwen2.5-14b-instruct-q4": {
        "repo_id": "bartowski/Qwen2.5-14B-Instruct-GGUF",
        "filename": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "description": "Qwen2.5 14B Instruct Q4_K_M (EXCELLENT function calling, larger model)",
        "function_calling": "excellent",
    },
    "mistral-7b-instruct-v0.3-q4": {
        "repo_id": "TheBloke/Mistral-7B-Instruct-v0.3-GGUF",
        "filename": "mistral-7b-instruct-v0.3.Q4_K_M.gguf",
        "description": "Mistral 7B Instruct v0.3 Q4_K_M (GOOD function calling)",
        "function_calling": "good",
    },
    "mistral-7b-instruct-v0.3-q5": {
        "repo_id": "TheBloke/Mistral-7B-Instruct-v0.3-GGUF",
        "filename": "mistral-7b-instruct-v0.3.Q5_K_M.gguf",
        "description": "Mistral 7B Instruct v0.3 Q5_K_M (GOOD function calling, higher quality)",
        "function_calling": "good",
    },
    "phi-3-mini-q4": {
        "repo_id": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "filename": "Phi-3-mini-4k-instruct-q4.gguf",
        "description": "Phi-3 Mini 4K Instruct Q4 (small, ~2.3GB, fast, limited function calling)",
        "function_calling": "limited",
    },
    "tinyllama-1.1b-chat-q4": {
        "repo_id": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        "filename": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "description": "TinyLlama 1.1B Chat Q4_K_M (very small, ~670MB, CPU-friendly, limited function calling)",
        "function_calling": "limited",
    },
    "llama-3.1-8b-instruct-q4": {
        "repo_id": "TheBloke/Llama-3.1-8B-Instruct-GGUF",
        "filename": "llama-3.1-8b-instruct.Q4_K_M.gguf",
        "description": "Llama 3.1 8B Instruct Q4_K_M (moderate function calling)",
        "function_calling": "moderate",
    },
    "llama-3.1-8b-instruct-q5": {
        "repo_id": "bartowski/Llama-3.1-8B-Instruct-GGUF",
        "filename": "Llama-3.1-8B-Instruct-Q5_K_M.gguf",
        "description": "Llama 3.1 8B Instruct Q5_K_M (moderate function calling, higher quality)",
        "function_calling": "moderate",
    },
    "llama-3.2-8b-instruct-q4": {
        "repo_id": "bartowski/Llama-3.2-8B-Instruct-GGUF",
        "filename": "Llama-3.2-8B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.2 8B Instruct Q4_K_M (better function calling than 3.1)",
        "function_calling": "good",
    },
    "llama-3.2-8b-instruct-q5": {
        "repo_id": "bartowski/Llama-3.2-8B-Instruct-GGUF",
        "filename": "Llama-3.2-8B-Instruct-Q5_K_M.gguf",
        "description": "Llama 3.2 8B Instruct Q5_K_M (better function calling than 3.1, higher quality)",
        "function_calling": "good",
    },
    "llama-3.3-70b-instruct-q4": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.3 70B Instruct Q4_K_M (large model, requires significant RAM)",
        "function_calling": "excellent",
    },
    "llama-3.3-70b-instruct-q5": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q5_K_M.gguf",
        "description": "Llama 3.3 70B Instruct Q5_K_M (large model, requires significant RAM)",
        "function_calling": "excellent",
    },
    "qwen3-32b-instruct": {
        "repo_id": "Qwen/Qwen3-32B-Instruct",
        "filename": None,
        "description": "Qwen3 32B Instruct (128K context, Transformers format, requires 80GB+ VRAM)",
        "function_calling": "excellent",
        "backend": "transformers",
    },
    "qwen3-14b-instruct": {
        "repo_id": "Qwen/Qwen3-14B-Instruct",
        "filename": None,
        "description": "Qwen3 14B Instruct (128K context, Transformers format)",
        "function_calling": "excellent",
        "backend": "transformers",
    },
    "qwen3-8b-instruct": {
        "repo_id": "Qwen/Qwen3-8B-Instruct",
        "filename": None,
        "description": "Qwen3 8B Instruct (32K context, extendable to 128K, Transformers format)",
        "function_calling": "excellent",
        "backend": "transformers",
    },
    "qwen3-30b-a3b-moe": {
        "repo_id": "Qwen/Qwen3-30B-A3B",
        "filename": None,
        "description": "Qwen3 30B-A3B MoE (128K context, ~3.3B active params, Transformers format)",
        "function_calling": "excellent",
        "backend": "transformers",
    },
}


def download_with_hf_hub(
    repo_id: str, filename: str, output_dir: Path, token: str | None = None
) -> Path:
    """Download model using huggingface_hub"""
    print(f"Downloading {filename} from {repo_id}...")
    print("This may take a while depending on your connection speed...")

    output_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=str(output_dir),
        local_dir_use_symlinks=False,
        token=token,
    )

    return Path(output_path)


def download_with_requests(
    repo_id: str, filename: str, output_dir: Path, token: str | None = None
) -> Path:
    """Download model using requests (fallback)"""
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError:
        print("Error: requests library is required for downloading without huggingface_hub")
        print("Install it with: pip install requests")
        sys.exit(1)

    url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
    output_path = output_dir / filename

    print(f"Downloading {filename} from {url}...")
    print("This may take a while depending on your connection speed...")

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(
                        f"\rProgress: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB)",
                        end="",
                        flush=True,
                    )

    print()

    return output_path


def download_model(
    model_key: str,
    output_dir: Path | None = None,
    token: str | None = None,
) -> Path:
    """Download a model (GGUF or HuggingFace Transformers)"""
    if model_key not in MODEL_CONFIGS:
        print(f"Error: Unknown model '{model_key}'")
        print("\nAvailable models:")
        print("\n⭐ RECOMMENDED for Function Calling (7B-14B):")
        for key, config in MODEL_CONFIGS.items():
            if config.get("function_calling") == "excellent" and (
                "7b" in key.lower() or "14b" in key.lower()
            ):
                print(f"  {key}: {config['description']}")
        print("\nGood Function Calling (7B-8B):")
        for key, config in MODEL_CONFIGS.items():
            if config.get("function_calling") == "good" and (
                "7b" in key.lower() or "8b" in key.lower()
            ):
                print(f"  {key}: {config['description']}")
        print("\nOther 7B-8B Models:")
        for key, config in MODEL_CONFIGS.items():
            if ("7b" in key.lower() or "8b" in key.lower()) and config.get(
                "function_calling"
            ) not in ["excellent", "good"]:
                print(f"  {key}: {config['description']}")
        print("\n70B+ Models (requires significant RAM/VRAM, 16GB+ recommended):")
        for key, config in MODEL_CONFIGS.items():
            if any(x in key.lower() for x in ["70b", "72b", "32b", "30b"]):
                print(f"  {key}: {config['description']}")
        sys.exit(1)

    config = MODEL_CONFIGS[model_key]
    backend = config.get("backend", "llama_cpp")

    if any(x in model_key.lower() for x in ["70b", "72b", "32b", "30b"]):
        print("⚠️  Warning: This is a large model which requires significant resources:")
        if backend == "transformers":
            print("   - VRAM: 40GB+ recommended (80GB+ for 32B)")
            print("   - Model size: ~20-70GB depending on model")
        else:
            print("   - RAM: 16GB+ recommended (32GB+ for Q6)")
            print("   - VRAM: 8GB+ recommended if using GPU acceleration")
            print("   - Model size: ~40-50GB (Q4) to ~60GB+ (Q6)")
        response = input("Continue with download? (y/N): ")
        if response.lower() != "y":
            print("Download cancelled.")
            sys.exit(0)

    if output_dir is None:
        output_dir = Path.home() / ".zikos" / "models"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    if backend == "transformers":
        if not HAS_HF_HUB:
            print("Error: huggingface_hub is required for Transformers models")
            print("Install it with: pip install huggingface_hub")
            sys.exit(1)

        output_path = output_dir / config["repo_id"].replace("/", "_")

        if output_path.exists():
            print(f"Model directory already exists at {output_path}")
            response = input("Do you want to re-download it? (y/N): ")
            if response.lower() != "y":
                print(f"Using existing model at {output_path}")
                return output_path

        print(f"Downloading Transformers model from {config['repo_id']}...")
        print("This may take a while depending on your connection speed...")

        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=config["repo_id"],
            local_dir=str(output_path),
            local_dir_use_symlinks=False,
            token=token,
        )

        print(f"\nModel downloaded successfully to: {output_path}")
        print("\nTo use this model, set the environment variable:")
        print(f"  export LLM_MODEL_PATH={output_path}")
        print("  export LLM_BACKEND=transformers")
        print("\nOr add it to your .env file:")
        print(f"  LLM_MODEL_PATH={output_path}")
        print("  LLM_BACKEND=transformers")

        return output_path
    else:
        output_path = output_dir / config["filename"]

        if output_path.exists():
            print(f"Model already exists at {output_path}")
            response = input("Do you want to re-download it? (y/N): ")
            if response.lower() != "y":
                print(f"Using existing model at {output_path}")
                return output_path
            output_path.unlink()

        try:
            if HAS_HF_HUB:
                try:
                    output_path = download_with_hf_hub(
                        config["repo_id"], config["filename"], output_dir, token
                    )
                except Exception as hf_error:
                    print(f"huggingface_hub failed: {hf_error}")
                    print("Trying direct download...")
                    output_path = download_with_requests(
                        config["repo_id"], config["filename"], output_dir, token
                    )
            else:
                output_path = download_with_requests(
                    config["repo_id"], config["filename"], output_dir, token
                )

            print(f"\nModel downloaded successfully to: {output_path}")
            print("\nTo use this model, set the environment variable:")
            print(f"  export LLM_MODEL_PATH={output_path}")
            print("\nOr add it to your .env file:")
            print(f"  LLM_MODEL_PATH={output_path}")

            return output_path

        except Exception as e:
            print(f"\nError downloading model: {e}")
            if "404" in str(e) or "Not Found" in str(e):
                print("\n⚠️  The model file may not be available at the expected location.")
                print("This could mean:")
                print("  1. The model hasn't been converted to GGUF format yet")
                print("  2. The filename or repository path has changed")
                print("  3. The model requires authentication")
                print("\nTry:")
                print(
                    "  - Check the repository on HuggingFace: https://huggingface.co/"
                    + config["repo_id"]
                )
                print("  - Try an alternative model like 'mistral-7b-instruct-v0.3-q4'")
                print("  - Or use 'llama-3.2-8b-instruct-q4' as a fallback")
            elif "401" in str(e) or "Unauthorized" in str(e):
                print("\n⚠️  Authentication error or repository not found.")
                print("This could mean:")
                print("  1. The repository doesn't exist or has been moved")
                print("  2. The model isn't available in GGUF format yet")
                print("  3. You need a HuggingFace token (unlikely for public models)")
                print("\nTry:")
                print(
                    "  - Check if the repository exists: https://huggingface.co/"
                    + config["repo_id"]
                )
                print("  - Try an alternative model:")
                print("    * 'mistral-7b-instruct-v0.3-q4' (GOOD function calling)")
                print("    * 'llama-3.2-8b-instruct-q4' (GOOD function calling)")
                print("  - Install huggingface_hub for better download handling:")
                print("    pip install huggingface_hub")
            if output_path.exists():
                output_path.unlink()
            sys.exit(1)


def list_models():
    """List available models"""
    print("Available models:\n")
    print("⭐ RECOMMENDED for Function Calling (7B-14B):")
    print("-" * 70)
    for key, config in MODEL_CONFIGS.items():
        if config.get("function_calling") == "excellent" and (
            "7b" in key.lower() or "14b" in key.lower()
        ):
            print(f"  {key}")
            print(f"    {config['description']}")
            print(f"    Repository: {config['repo_id']}")
            print(f"    File: {config['filename']}")
            print()

    print("\nGood Function Calling (7B-8B):")
    print("-" * 70)
    for key, config in MODEL_CONFIGS.items():
        if config.get("function_calling") == "good" and (
            "7b" in key.lower() or "8b" in key.lower()
        ):
            print(f"  {key}")
            print(f"    {config['description']}")
            print(f"    Repository: {config['repo_id']}")
            print(f"    File: {config['filename']}")
            print()

    print("\nOther 7B-8B Models:")
    print("-" * 70)
    for key, config in MODEL_CONFIGS.items():
        if ("7b" in key.lower() or "8b" in key.lower()) and config.get("function_calling") not in [
            "excellent",
            "good",
        ]:
            print(f"  {key}")
            print(f"    {config['description']}")
            print(f"    Repository: {config['repo_id']}")
            print(f"    File: {config['filename']}")
            print()

        print("\n70B+ Models (requires significant RAM/VRAM, 16GB+ recommended):")
        print("-" * 70)
        for key, config in MODEL_CONFIGS.items():
            if any(x in key.lower() for x in ["70b", "72b", "32b", "30b"]):
                print(f"  {key}")
                print(f"    {config['description']}")
                print(f"    Repository: {config['repo_id']}")
                if config.get("filename"):
                    print(f"    File: {config['filename']}")
                if config.get("backend"):
                    print(f"    Backend: {config['backend']}")
                print()


def main():
    parser = argparse.ArgumentParser(description="Download Llama models in GGUF format for Zikos")
    parser.add_argument(
        "model",
        nargs="?",
        help="Model to download (use --list to see available models)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory (default: ~/.zikos/models)",
    )
    parser.add_argument(
        "-t",
        "--token",
        help="Hugging Face token (optional, for private models)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models",
    )

    args = parser.parse_args()

    if args.list:
        list_models()
        return

    if not args.model:
        parser.print_help()
        print("\nUse --list to see available models")
        sys.exit(1)

    download_model(args.model, args.output, args.token)


if __name__ == "__main__":
    main()
