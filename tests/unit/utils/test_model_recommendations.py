"""Tests for model recommendations based on hardware"""

import pytest

from zikos.utils.gpu import GpuInfo, HardwareProfile, RamInfo
from zikos.utils.model_recommendations import (
    AVAILABLE_MODELS,
    get_default_model_path,
    get_hardware_tier,
    get_primary_recommendation,
    get_recommended_models,
)


def make_profile(
    gpu_available: bool = False,
    vram_total: float | None = None,
    vram_free: float | None = None,
    ram_total: float = 16.0,
    ram_available: float = 12.0,
) -> HardwareProfile:
    """Helper to create HardwareProfile for testing"""
    return HardwareProfile(
        gpu=GpuInfo(
            available=gpu_available,
            device=0 if gpu_available else None,
            name="Test GPU" if gpu_available else None,
            memory_total_gb=vram_total,
            memory_free_gb=vram_free,
        ),
        ram=RamInfo(total_gb=ram_total, available_gb=ram_available),
        gpu_hint=None,
    )


class TestGetHardwareTier:
    def test_very_high_tier_with_24gb_vram(self):
        profile = make_profile(gpu_available=True, vram_total=24.0, vram_free=20.0)
        assert get_hardware_tier(profile) == "very_high"

    def test_high_tier_with_16gb_vram(self):
        profile = make_profile(gpu_available=True, vram_total=16.0, vram_free=14.0)
        assert get_hardware_tier(profile) == "high"

    def test_medium_tier_with_8gb_vram(self):
        profile = make_profile(gpu_available=True, vram_total=8.0, vram_free=6.0)
        assert get_hardware_tier(profile) == "medium"

    def test_low_tier_with_4gb_vram(self):
        profile = make_profile(gpu_available=True, vram_total=4.0, vram_free=3.0)
        assert get_hardware_tier(profile) == "low"

    def test_cpu_tier_with_no_gpu(self):
        profile = make_profile(gpu_available=False, ram_available=8.0)
        assert get_hardware_tier(profile) == "cpu"

    def test_low_tier_cpu_with_lots_of_ram(self):
        profile = make_profile(gpu_available=False, ram_available=32.0)
        assert get_hardware_tier(profile) == "low"


class TestGetRecommendedModels:
    def test_returns_models_for_high_end_gpu(self):
        profile = make_profile(gpu_available=True, vram_total=24.0, vram_free=20.0)
        models = get_recommended_models(profile)

        assert len(models) > 0
        # Should include larger models for high-end hardware
        model_names = [m.name for m in models]
        assert "Qwen3-14B" in model_names
        assert "Qwen3-8B" in model_names

    def test_returns_small_models_for_cpu_only(self):
        profile = make_profile(gpu_available=False, ram_available=8.0)
        models = get_recommended_models(profile)

        assert len(models) > 0
        # Should only include CPU-friendly models
        for model in models:
            assert model.ram_required_gb <= 8.0

    def test_models_sorted_by_quality_descending(self):
        profile = make_profile(gpu_available=True, vram_total=24.0, vram_free=20.0)
        models = get_recommended_models(profile)

        # Best models should come first
        if len(models) > 1:
            tier_order = ["cpu", "low", "medium", "high", "very_high"]
            for i in range(len(models) - 1):
                current_tier = tier_order.index(models[i].tier)
                next_tier = tier_order.index(models[i + 1].tier)
                assert current_tier >= next_tier

    def test_returns_empty_for_insufficient_resources(self):
        # Very low RAM and no GPU
        profile = make_profile(gpu_available=False, ram_available=1.0)
        models = get_recommended_models(profile)
        assert models == []


class TestGetPrimaryRecommendation:
    def test_returns_best_model(self):
        profile = make_profile(gpu_available=True, vram_total=16.0, vram_free=14.0)
        model = get_primary_recommendation(profile)

        assert model is not None
        assert model.vram_required_gb <= 14.0

    def test_returns_none_for_insufficient_resources(self):
        profile = make_profile(gpu_available=False, ram_available=1.0)
        model = get_primary_recommendation(profile)
        assert model is None


class TestAvailableModels:
    def test_all_models_have_required_fields(self):
        for model in AVAILABLE_MODELS:
            assert model.name
            assert model.filename
            assert model.size_gb > 0
            assert model.vram_required_gb > 0
            assert model.ram_required_gb > 0
            assert model.context_window > 0
            assert model.download_url.startswith("https://")
            assert model.description
            assert model.tier in ["cpu", "low", "medium", "high", "very_high"]

    def test_download_urls_are_valid_huggingface_urls(self):
        for model in AVAILABLE_MODELS:
            assert "huggingface.co" in model.download_url
            assert model.filename in model.download_url


class TestGetDefaultModelPath:
    def test_returns_path_in_home_directory(self):
        path = get_default_model_path()
        assert "models" in path
        assert path.startswith("/")
