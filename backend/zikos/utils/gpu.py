"""GPU detection and optimization utilities"""

import os
from typing import Any


def detect_gpu() -> dict[str, Any]:
    """Detect available GPU and return information"""
    gpu_info: dict[str, Any] = {
        "available": False,
        "device": None,
        "name": None,
        "memory_total_gb": None,
        "memory_free_gb": None,
    }

    try:
        import torch

        if torch.cuda.is_available():
            gpu_info["available"] = True
            gpu_info["device"] = torch.cuda.current_device()
            gpu_info["name"] = torch.cuda.get_device_name(0)
            gpu_info["memory_total_gb"] = torch.cuda.get_device_properties(0).total_memory / (
                1024**3
            )
            gpu_info["memory_free_gb"] = (
                torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
            ) / (1024**3)
    except ImportError:
        pass

    if not gpu_info["available"]:
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines:
                    parts = lines[0].split(",")
                    if len(parts) >= 2:
                        gpu_info["available"] = True
                        gpu_info["name"] = parts[0].strip()
                        memory_str = parts[1].strip().replace(" MiB", "").replace(" MB", "")
                        try:
                            gpu_info["memory_total_gb"] = float(memory_str) / 1024
                        except ValueError:
                            pass
        except Exception:
            pass

    return gpu_info


def get_optimal_gpu_layers(model_path: str, backend_type: str = "auto") -> int:
    """Get optimal number of GPU layers for a model

    Returns -1 for full GPU offload, 0 for CPU only, or specific layer count
    """
    gpu_info = detect_gpu()

    if not gpu_info["available"]:
        return 0

    model_path_lower = str(model_path).lower()

    if backend_type == "transformers" or (
        backend_type == "auto" and not model_path_lower.endswith(".gguf")
    ):
        return -1

    if "70b" in model_path_lower or "72b" in model_path_lower:
        if gpu_info["memory_total_gb"] and gpu_info["memory_total_gb"] >= 80:
            return -1
        elif gpu_info["memory_total_gb"] and gpu_info["memory_total_gb"] >= 40:
            return 60
        else:
            return 40
    elif "32b" in model_path_lower:
        if gpu_info["memory_total_gb"] and gpu_info["memory_total_gb"] >= 40:
            return -1
        else:
            return 40
    elif "14b" in model_path_lower:
        if gpu_info["memory_total_gb"] and gpu_info["memory_total_gb"] >= 24:
            return -1
        else:
            return 35
    elif "8b" in model_path_lower or "7b" in model_path_lower:
        if gpu_info["memory_total_gb"] and gpu_info["memory_total_gb"] >= 16:
            return -1
        else:
            return 35

    return -1
