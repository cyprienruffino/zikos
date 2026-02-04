"""Hardware detection and optimization utilities"""

import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class GpuInfo:
    available: bool
    device: int | None = None
    name: str | None = None
    memory_total_gb: float | None = None
    memory_free_gb: float | None = None


@dataclass
class RamInfo:
    total_gb: float
    available_gb: float


@dataclass
class GpuHint:
    hint_type: str  # "no_gpu_detected" | "cuda_not_configured"
    message: str
    docs_url: str


@dataclass
class HardwareProfile:
    gpu: GpuInfo
    ram: RamInfo
    gpu_hint: GpuHint | None = None


def _check_nvidia_smi() -> dict[str, Any] | None:
    """Check if nvidia-smi can detect a GPU (even if CUDA isn't available to Python)"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines and lines[0]:
                parts = lines[0].split(",")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    memory_total_str = parts[1].strip().replace(" MiB", "").replace(" MB", "")
                    memory_free_str = (
                        parts[2].strip().replace(" MiB", "").replace(" MB", "")
                        if len(parts) >= 3
                        else None
                    )
                    try:
                        memory_total_gb = float(memory_total_str) / 1024
                        memory_free_gb = float(memory_free_str) / 1024 if memory_free_str else None
                        return {
                            "name": name,
                            "memory_total_gb": memory_total_gb,
                            "memory_free_gb": memory_free_gb,
                        }
                    except ValueError:
                        return {"name": name, "memory_total_gb": None, "memory_free_gb": None}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def detect_gpu() -> dict[str, Any]:
    """Detect available GPU and return information (legacy dict interface)"""
    gpu_info = detect_gpu_info()
    return {
        "available": gpu_info.available,
        "device": gpu_info.device,
        "name": gpu_info.name,
        "memory_total_gb": gpu_info.memory_total_gb,
        "memory_free_gb": gpu_info.memory_free_gb,
    }


def detect_gpu_info() -> GpuInfo:
    """Detect available GPU and return structured GpuInfo"""
    gpu_info = GpuInfo(available=False)

    # Try PyTorch CUDA first
    try:
        import torch

        if torch.cuda.is_available():
            gpu_info.available = True
            gpu_info.device = torch.cuda.current_device()
            gpu_info.name = torch.cuda.get_device_name(0)
            gpu_info.memory_total_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            gpu_info.memory_free_gb = (
                torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
            ) / (1024**3)
            return gpu_info
    except ImportError:
        pass

    # Fallback to nvidia-smi if CUDA not available to Python
    nvidia_info = _check_nvidia_smi()
    if nvidia_info:
        gpu_info.available = True
        gpu_info.name = nvidia_info["name"]
        gpu_info.memory_total_gb = nvidia_info["memory_total_gb"]
        gpu_info.memory_free_gb = nvidia_info["memory_free_gb"]

    return gpu_info


def detect_ram() -> RamInfo:
    """Detect system RAM"""
    try:
        import psutil

        mem = psutil.virtual_memory()
        return RamInfo(
            total_gb=mem.total / (1024**3),
            available_gb=mem.available / (1024**3),
        )
    except ImportError:
        # Fallback to /proc/meminfo on Linux
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]  # Get numeric part
                        meminfo[key] = int(value) * 1024  # Convert KB to bytes

                total = meminfo.get("MemTotal", 0)
                available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                return RamInfo(
                    total_gb=total / (1024**3),
                    available_gb=available / (1024**3),
                )
        except (FileNotFoundError, OSError, ValueError, KeyError):
            # Last resort fallback
            return RamInfo(total_gb=8.0, available_gb=4.0)


def detect_hardware() -> HardwareProfile:
    """Detect full hardware profile including GPU, RAM, and helpful hints"""
    gpu_info = detect_gpu_info()
    ram_info = detect_ram()
    gpu_hint = None

    if not gpu_info.available:
        # Check if nvidia-smi sees a GPU even though CUDA isn't available to Python
        cuda_available_to_python = False
        try:
            import torch

            cuda_available_to_python = torch.cuda.is_available()
        except ImportError:
            pass

        nvidia_smi_info = _check_nvidia_smi()

        if nvidia_smi_info and not cuda_available_to_python:
            # GPU detected by nvidia-smi but CUDA not available to Python
            gpu_hint = GpuHint(
                hint_type="cuda_not_configured",
                message=(
                    f"NVIDIA GPU detected ({nvidia_smi_info['name']}) but CUDA is not available "
                    "to Python. Your PyTorch installation may not have CUDA support."
                ),
                docs_url="https://pytorch.org/get-started/locally/",
            )
            # Update gpu_info with nvidia-smi data for display
            gpu_info.name = nvidia_smi_info["name"]
            gpu_info.memory_total_gb = nvidia_smi_info["memory_total_gb"]
            gpu_info.memory_free_gb = nvidia_smi_info["memory_free_gb"]
        else:
            gpu_hint = GpuHint(
                hint_type="no_gpu_detected",
                message=(
                    "No GPU detected. If you have an NVIDIA GPU, ensure CUDA drivers are "
                    "installed and PyTorch is built with CUDA support."
                ),
                docs_url="https://docs.nvidia.com/cuda/cuda-installation-guide-linux/",
            )

    return HardwareProfile(gpu=gpu_info, ram=ram_info, gpu_hint=gpu_hint)


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
