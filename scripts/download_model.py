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
    "llama-3.1-8b-instruct-q4": {
        "repo_id": "bartowski/Llama-3.1-8B-Instruct-GGUF",
        "filename": "Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.1 8B Instruct Q4_K_M (recommended balance)",
    },
    "llama-3.1-8b-instruct-q5": {
        "repo_id": "bartowski/Llama-3.1-8B-Instruct-GGUF",
        "filename": "Llama-3.1-8B-Instruct-Q5_K_M.gguf",
        "description": "Llama 3.1 8B Instruct Q5_K_M (higher quality)",
    },
    "llama-3.1-8b-instruct-q8": {
        "repo_id": "bartowski/Llama-3.1-8B-Instruct-GGUF",
        "filename": "Llama-3.1-8B-Instruct-Q8_0.gguf",
        "description": "Llama 3.1 8B Instruct Q8_0 (very high quality)",
    },
    "llama-3.2-8b-instruct-q4": {
        "repo_id": "bartowski/Llama-3.2-8B-Instruct-GGUF",
        "filename": "Llama-3.2-8B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.2 8B Instruct Q4_K_M (recommended balance)",
    },
    "llama-3.2-8b-instruct-q5": {
        "repo_id": "bartowski/Llama-3.2-8B-Instruct-GGUF",
        "filename": "Llama-3.2-8B-Instruct-Q5_K_M.gguf",
        "description": "Llama 3.2 8B Instruct Q5_K_M (higher quality)",
    },
    "llama-3.3-70b-instruct-q4": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.3 70B Instruct Q4_K_M (large model, requires significant RAM)",
    },
    "llama-3.3-70b-instruct-q5": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q5_K_M.gguf",
        "description": "Llama 3.3 70B Instruct Q5_K_M (large model, requires significant RAM)",
    },
    "llama-3.3-70b-instruct-q6": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q6_K.gguf",
        "description": "Llama 3.3 70B Instruct Q6_K (large model, very high quality)",
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
    """Download a Llama model"""
    if model_key not in MODEL_CONFIGS:
        print(f"Error: Unknown model '{model_key}'")
        print("\nAvailable models:")
        print("\n8B Models (recommended for most systems):")
        for key, config in MODEL_CONFIGS.items():
            if "8b" in key.lower():
                print(f"  {key}: {config['description']}")
        print("\n70B Models (requires significant RAM/VRAM, 16GB+ recommended):")
        for key, config in MODEL_CONFIGS.items():
            if "70b" in key.lower():
                print(f"  {key}: {config['description']}")
        sys.exit(1)

    config = MODEL_CONFIGS[model_key]

    if "70b" in model_key.lower():
        print("⚠️  Warning: This is a 70B model which requires significant resources:")
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
            output_path = download_with_hf_hub(
                config["repo_id"], config["filename"], output_dir, token
            )
        else:
            output_path = download_with_requests(
                config["repo_id"], config["filename"], output_dir, token
            )

        print(f"\n✓ Model downloaded successfully to: {output_path}")
        print("\nTo use this model, set the environment variable:")
        print(f"  export LLM_MODEL_PATH={output_path}")
        print("\nOr add it to your .env file:")
        print(f"  LLM_MODEL_PATH={output_path}")

        return output_path

    except Exception as e:
        print(f"\n✗ Error downloading model: {e}")
        if output_path.exists():
            output_path.unlink()
        sys.exit(1)


def list_models():
    """List available models"""
    print("Available models:\n")
    print("8B Models (recommended for most systems):")
    print("-" * 60)
    for key, config in MODEL_CONFIGS.items():
        if "8b" in key.lower():
            print(f"  {key}")
            print(f"    {config['description']}")
            print(f"    Repository: {config['repo_id']}")
            print(f"    File: {config['filename']}")
            print()

    print("\n70B Models (requires significant RAM/VRAM):")
    print("-" * 60)
    for key, config in MODEL_CONFIGS.items():
        if "70b" in key.lower():
            print(f"  {key}")
            print(f"    {config['description']}")
            print(f"    Repository: {config['repo_id']}")
            print(f"    File: {config['filename']}")
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
