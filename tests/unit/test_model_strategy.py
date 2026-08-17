"""Tests for model strategy"""

from zikos.services.llm_orchestration.tool_call_parser import (
    HybridToolCallParser,
    NativeToolCallParser,
    QwenToolCallParser,
    SimplifiedToolCallParser,
)
from zikos.services.model_strategy import (
    ModelStrategy,
    SamplingParams,
    ThinkingConfig,
    get_model_strategy,
)
from zikos.services.tool_providers.qwen_tool_provider import QwenToolProvider
from zikos.services.tool_providers.simplified_tool_provider import SimplifiedToolProvider
from zikos.services.tool_providers.structured_tool_provider import StructuredToolProvider


class TestGetModelStrategy:
    def test_explicit_qwen_format(self):
        s = get_model_strategy(tool_format="qwen")
        assert isinstance(s.tool_provider, QwenToolProvider)
        assert isinstance(s.tool_call_parser, QwenToolCallParser)

    def test_explicit_simplified_format(self):
        s = get_model_strategy(tool_format="simplified")
        assert isinstance(s.tool_provider, SimplifiedToolProvider)
        # Explicit 'simplified' must yield the simplified parser, not hybrid
        assert isinstance(s.tool_call_parser, SimplifiedToolCallParser)

    def test_explicit_native_format(self):
        s = get_model_strategy(tool_format="native")
        assert isinstance(s.tool_provider, StructuredToolProvider)
        assert isinstance(s.tool_call_parser, NativeToolCallParser)

    def test_auto_detect_qwen25(self):
        s = get_model_strategy(model_path="/models/qwen2.5-7b.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, QwenToolProvider)
        assert s.thinking.enabled is True
        assert s.thinking.prompt_suffix == "/think"

    def test_auto_detect_qwen3(self):
        s = get_model_strategy(model_path="Qwen/Qwen3-32B", tool_format="auto")
        assert isinstance(s.tool_provider, QwenToolProvider)
        assert s.preferred_backend == "transformers"
        assert s.sampling.top_p == 0.8

    def test_auto_detect_mistral(self):
        s = get_model_strategy(model_path="/models/mistral-7b.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, SimplifiedToolProvider)
        assert isinstance(s.tool_call_parser, SimplifiedToolCallParser)

    def test_auto_detect_phi(self):
        s = get_model_strategy(model_path="/models/phi-3-mini.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, SimplifiedToolProvider)
        assert s.sampling.temperature == 0.6

    def test_auto_detect_llama(self):
        s = get_model_strategy(model_path="/models/llama-3.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, SimplifiedToolProvider)

    def test_auto_detect_native_keywords(self):
        s = get_model_strategy(model_path="gpt-4", tool_format="auto")
        assert isinstance(s.tool_provider, StructuredToolProvider)

    def test_unknown_model_defaults(self):
        s = get_model_strategy(model_path="/models/unknown.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, SimplifiedToolProvider)
        assert isinstance(s.tool_call_parser, HybridToolCallParser)

    def test_generic_qwen_gets_qwen_strategy(self):
        """qwen2 / generic qwen models must not fall through to the
        Simplified default."""
        s = get_model_strategy(model_path="/models/qwen2-7b-instruct.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, QwenToolProvider)
        assert isinstance(s.tool_call_parser, QwenToolCallParser)

    def test_cloud_provider_setting_forces_native(self, monkeypatch):
        """Any provider in the create_backend cloud table must get the native
        strategy, even for models whose names match local families."""
        from zikos.config import settings

        for provider in ("gemini", "mistral", "groq", "together", "cohere"):
            monkeypatch.setattr(settings, "llm_provider", provider)
            s = get_model_strategy(model_path="whatever-model", tool_format="auto")
            assert isinstance(s.tool_provider, StructuredToolProvider), provider
            assert isinstance(s.tool_call_parser, NativeToolCallParser), provider

    def test_cloud_provider_prefix_path_forces_native(self, monkeypatch):
        """provider/model paths route to native — notably mistral/... must not
        be captured by the local Mistral detection."""
        from zikos.config import settings

        monkeypatch.setattr(settings, "llm_provider", "")
        for path in (
            "gemini/gemini-2.0-flash",
            "mistral/mistral-large-latest",
            "groq/llama-3.3-70b",
            "together/qwen2.5-72b",
            "cohere/command-r-plus",
        ):
            s = get_model_strategy(model_path=path, tool_format="auto")
            assert isinstance(s.tool_provider, StructuredToolProvider), path
            assert isinstance(s.tool_call_parser, NativeToolCallParser), path

    def test_local_mistral_path_still_simplified(self, monkeypatch):
        from zikos.config import settings

        monkeypatch.setattr(settings, "llm_provider", "")
        s = get_model_strategy(model_path="/models/mistral-7b.gguf", tool_format="auto")
        assert isinstance(s.tool_provider, SimplifiedToolProvider)

    def test_returns_copy(self):
        s1 = get_model_strategy(tool_format="qwen")
        s2 = get_model_strategy(tool_format="qwen")
        assert s1 is not s2
        assert s1.sampling is not s2.sampling


class TestSamplingParams:
    def test_defaults(self):
        p = SamplingParams()
        assert p.temperature == 0.7
        assert p.top_p == 0.9
        assert p.top_k == 40


class TestThinkingConfig:
    def test_defaults(self):
        t = ThinkingConfig()
        assert t.enabled is False
        assert t.prompt_suffix == ""
        assert t.max_tokens == 0

    def test_enabled(self):
        t = ThinkingConfig(enabled=True, prompt_suffix="/think")
        assert t.enabled is True
        assert t.prompt_suffix == "/think"


class TestModelStrategy:
    def test_construction(self):
        s = ModelStrategy(
            tool_provider=SimplifiedToolProvider(),
            tool_call_parser=HybridToolCallParser(),
        )
        assert s.preferred_backend == "auto"
        assert s.sampling.temperature == 0.7
        assert s.thinking.enabled is False
