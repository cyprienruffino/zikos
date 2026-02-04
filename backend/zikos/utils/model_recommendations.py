"""Model recommendations based on hardware capabilities"""

from dataclasses import dataclass

from zikos.utils.gpu import HardwareProfile


@dataclass
class ModelRecommendation:
    name: str
    filename: str
    size_gb: float
    vram_required_gb: float  # Minimum VRAM for full GPU offload
    ram_required_gb: float  # RAM needed for CPU-only mode
    context_window: int
    download_url: str
    description: str
    tier: str  # "cpu" | "low" | "medium" | "high" | "very_high"


# Qwen3 GGUF models from https://huggingface.co/Qwen
# Using Q4_K_M quantization as good balance of quality/size
AVAILABLE_MODELS: list[ModelRecommendation] = [
    ModelRecommendation(
        name="Qwen3-0.6B",
        filename="qwen3-0_6b-q4_k_m.gguf",
        size_gb=0.5,
        vram_required_gb=1.0,
        ram_required_gb=2.0,
        context_window=32768,
        download_url="https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/qwen3-0_6b-q4_k_m.gguf",
        description="Tiny model for very limited hardware. Basic capabilities.",
        tier="cpu",
    ),
    ModelRecommendation(
        name="Qwen3-1.7B",
        filename="qwen3-1_7b-q4_k_m.gguf",
        size_gb=1.2,
        vram_required_gb=2.0,
        ram_required_gb=4.0,
        context_window=32768,
        download_url="https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/qwen3-1_7b-q4_k_m.gguf",
        description="Small model for CPU-only or low VRAM. Good for basic tasks.",
        tier="cpu",
    ),
    ModelRecommendation(
        name="Qwen3-4B",
        filename="qwen3-4b-q4_k_m.gguf",
        size_gb=2.8,
        vram_required_gb=4.0,
        ram_required_gb=6.0,
        context_window=32768,
        download_url="https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/qwen3-4b-q4_k_m.gguf",
        description="Balanced small model. Good quality for modest hardware.",
        tier="low",
    ),
    ModelRecommendation(
        name="Qwen3-8B",
        filename="qwen3-8b-q4_k_m.gguf",
        size_gb=5.0,
        vram_required_gb=8.0,
        ram_required_gb=10.0,
        context_window=32768,
        download_url="https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/qwen3-8b-q4_k_m.gguf",
        description="Strong mid-range model. Recommended for 8GB+ VRAM.",
        tier="medium",
    ),
    ModelRecommendation(
        name="Qwen3-14B",
        filename="qwen3-14b-q4_k_m.gguf",
        size_gb=9.0,
        vram_required_gb=12.0,
        ram_required_gb=16.0,
        context_window=32768,
        download_url="https://huggingface.co/Qwen/Qwen3-14B-GGUF/resolve/main/qwen3-14b-q4_k_m.gguf",
        description="High quality model. Recommended for 16GB+ VRAM.",
        tier="high",
    ),
    ModelRecommendation(
        name="Qwen3-32B",
        filename="qwen3-32b-q4_k_m.gguf",
        size_gb=20.0,
        vram_required_gb=24.0,
        ram_required_gb=32.0,
        context_window=32768,
        download_url="https://huggingface.co/Qwen/Qwen3-32B-GGUF/resolve/main/qwen3-32b-q4_k_m.gguf",
        description="Excellent quality. For high-end GPUs (24GB+ VRAM).",
        tier="very_high",
    ),
]


def get_hardware_tier(profile: HardwareProfile) -> str:
    """Determine hardware tier based on available resources"""
    if profile.gpu.available and profile.gpu.memory_total_gb:
        vram = profile.gpu.memory_total_gb
        if vram >= 24:
            return "very_high"
        elif vram >= 12:
            return "high"
        elif vram >= 8:
            return "medium"
        elif vram >= 4:
            return "low"

    # CPU-only or very low VRAM - check RAM
    if profile.ram.available_gb >= 16:
        return "low"  # Can run 4B on CPU
    return "cpu"


def get_recommended_models(profile: HardwareProfile) -> list[ModelRecommendation]:
    """Get list of models that can run on this hardware, sorted by recommendation

    Returns models that fit in available memory, with the best recommended model first.
    """
    tier = get_hardware_tier(profile)
    tier_order = ["cpu", "low", "medium", "high", "very_high"]
    max_tier_index = tier_order.index(tier)

    available_vram = profile.gpu.memory_free_gb if profile.gpu.available else 0
    available_ram = profile.ram.available_gb

    compatible_models = []
    for model in AVAILABLE_MODELS:
        model_tier_index = tier_order.index(model.tier)

        # Check if model fits in available memory
        can_run_on_gpu = available_vram and available_vram >= model.vram_required_gb
        can_run_on_cpu = available_ram >= model.ram_required_gb

        if can_run_on_gpu or can_run_on_cpu:
            # Model is compatible if it's at or below our tier
            if model_tier_index <= max_tier_index:
                compatible_models.append(model)

    # Sort by tier (descending) - best models first
    compatible_models.sort(key=lambda m: tier_order.index(m.tier), reverse=True)

    return compatible_models


def get_primary_recommendation(profile: HardwareProfile) -> ModelRecommendation | None:
    """Get the single best model recommendation for this hardware"""
    models = get_recommended_models(profile)
    return models[0] if models else None


def get_default_model_path() -> str:
    """Get the default path where users should save models"""
    import os

    home = os.path.expanduser("~")
    return os.path.join(home, "models")
