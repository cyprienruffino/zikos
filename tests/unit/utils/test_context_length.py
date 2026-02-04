"""Tests for context length estimation utilities"""

import pytest

from zikos.utils.context_length import (
    estimate_kv_cache_memory_gb,
    estimate_max_context_for_memory,
    estimate_model_base_memory_gb,
    get_recommended_context_length,
    parse_model_size,
)
from zikos.utils.gpu import GpuInfo, HardwareProfile, RamInfo


def make_profile(
    gpu_available: bool = False,
    vram_free: float | None = None,
    ram_available: float = 16.0,
) -> HardwareProfile:
    """Helper to create HardwareProfile for testing"""
    return HardwareProfile(
        gpu=GpuInfo(
            available=gpu_available,
            device=0 if gpu_available else None,
            name="Test GPU" if gpu_available else None,
            memory_total_gb=vram_free * 1.2 if vram_free else None,
            memory_free_gb=vram_free,
        ),
        ram=RamInfo(total_gb=ram_available * 1.2, available_gb=ram_available),
        gpu_hint=None,
    )


class TestParseModelSize:
    def test_parses_7b(self):
        assert parse_model_size("qwen3-7b-q4_k_m.gguf") == "7b"

    def test_parses_14b(self):
        assert parse_model_size("models/Qwen3-14B-Instruct.gguf") == "14b"

    def test_parses_decimal_sizes(self):
        assert parse_model_size("qwen3-0.6b-q4.gguf") == "0.6b"
        assert parse_model_size("qwen3-1.7b-q4.gguf") == "1.7b"

    def test_returns_none_for_no_match(self):
        assert parse_model_size("some-random-model.gguf") is None


class TestEstimateModelBaseMemory:
    def test_estimates_from_model_size_in_name(self):
        # 7B Q4 model should be around 4-5GB
        memory = estimate_model_base_memory_gb("qwen3-7b-q4_k_m.gguf")
        assert 4.0 < memory < 7.0

    def test_estimates_larger_for_14b(self):
        memory_7b = estimate_model_base_memory_gb("qwen3-7b.gguf")
        memory_14b = estimate_model_base_memory_gb("qwen3-14b.gguf")
        assert memory_14b > memory_7b

    def test_fallback_for_unknown_model(self):
        memory = estimate_model_base_memory_gb("unknown-model.gguf")
        # Should return reasonable default
        assert memory > 0


class TestEstimateKvCacheMemory:
    def test_scales_with_context_length(self):
        small_ctx = estimate_kv_cache_memory_gb("qwen3-7b.gguf", 4096)
        large_ctx = estimate_kv_cache_memory_gb("qwen3-7b.gguf", 32768)
        # 8x context should be ~8x memory
        assert large_ctx > small_ctx * 7

    def test_larger_models_need_more_memory(self):
        kv_7b = estimate_kv_cache_memory_gb("qwen3-7b.gguf", 8192)
        kv_32b = estimate_kv_cache_memory_gb("qwen3-32b.gguf", 8192)
        assert kv_32b > kv_7b


class TestEstimateMaxContextForMemory:
    def test_more_memory_allows_larger_context(self):
        ctx_8gb = estimate_max_context_for_memory("qwen3-7b.gguf", 8.0)
        ctx_16gb = estimate_max_context_for_memory("qwen3-7b.gguf", 16.0)
        assert ctx_16gb > ctx_8gb

    def test_respects_native_context_limit(self):
        ctx = estimate_max_context_for_memory(
            "qwen3-7b.gguf",
            available_memory_gb=64.0,  # Lots of memory
            native_context_length=8192,  # But model only supports 8K
        )
        assert ctx <= 8192

    def test_returns_minimum_when_memory_tight(self):
        ctx = estimate_max_context_for_memory("qwen3-14b.gguf", 2.0)
        # Should return minimum viable context
        assert ctx >= 2048

    def test_rounds_to_1024(self):
        ctx = estimate_max_context_for_memory("qwen3-7b.gguf", 10.0)
        assert ctx % 1024 == 0


class TestGetRecommendedContextLength:
    def test_uses_gpu_memory_when_available(self):
        profile = make_profile(gpu_available=True, vram_free=16.0, ram_available=32.0)
        ctx = get_recommended_context_length("qwen3-7b.gguf", profile)
        # Should be reasonable for 16GB VRAM
        assert 4096 <= ctx <= 65536

    def test_uses_ram_when_no_gpu(self):
        profile = make_profile(gpu_available=False, ram_available=16.0)
        ctx = get_recommended_context_length("qwen3-7b.gguf", profile)
        # Should be reasonable for 16GB RAM
        assert 4096 <= ctx <= 65536

    def test_respects_native_limit(self):
        profile = make_profile(gpu_available=True, vram_free=64.0)
        ctx = get_recommended_context_length("qwen3-7b.gguf", profile, native_context_length=4096)
        assert ctx <= 4096
