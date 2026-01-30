"""Model strategy - bundles all model-family-specific behavior"""

from dataclasses import dataclass, field

from zikos.services.llm_orchestration.tool_call_parser import (
    HybridToolCallParser,
    NativeToolCallParser,
    QwenToolCallParser,
    SimplifiedToolCallParser,
    ToolCallParser,
)
from zikos.services.tool_provider import ToolProvider
from zikos.services.tool_providers.qwen_tool_provider import QwenToolProvider
from zikos.services.tool_providers.simplified_tool_provider import SimplifiedToolProvider
from zikos.services.tool_providers.structured_tool_provider import StructuredToolProvider


@dataclass
class SamplingParams:
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40


@dataclass
class ThinkingConfig:
    enabled: bool = False
    prompt_suffix: str = ""
    max_tokens: int = 0  # 0 = unlimited when enabled


@dataclass
class ModelStrategy:
    tool_provider: ToolProvider
    tool_call_parser: ToolCallParser
    sampling: SamplingParams = field(default_factory=SamplingParams)
    thinking: ThinkingConfig = field(default_factory=ThinkingConfig)
    preferred_backend: str = "auto"


def _build_strategies() -> dict[str, ModelStrategy]:
    return {
        "qwen2.5": ModelStrategy(
            tool_provider=QwenToolProvider(),
            tool_call_parser=QwenToolCallParser(),
            sampling=SamplingParams(temperature=0.7, top_p=0.9),
            thinking=ThinkingConfig(enabled=True, prompt_suffix="/think"),
        ),
        "qwen3": ModelStrategy(
            tool_provider=QwenToolProvider(),
            tool_call_parser=QwenToolCallParser(),
            sampling=SamplingParams(temperature=0.6, top_p=0.8),
            thinking=ThinkingConfig(enabled=True, prompt_suffix="/think"),
            preferred_backend="transformers",
        ),
        "mistral": ModelStrategy(
            tool_provider=SimplifiedToolProvider(),
            tool_call_parser=SimplifiedToolCallParser(),
        ),
        "phi": ModelStrategy(
            tool_provider=SimplifiedToolProvider(),
            tool_call_parser=SimplifiedToolCallParser(),
            sampling=SamplingParams(temperature=0.6),
        ),
        "llama": ModelStrategy(
            tool_provider=SimplifiedToolProvider(),
            tool_call_parser=SimplifiedToolCallParser(),
        ),
        "native": ModelStrategy(
            tool_provider=StructuredToolProvider(),
            tool_call_parser=NativeToolCallParser(),
        ),
        "default": ModelStrategy(
            tool_provider=SimplifiedToolProvider(),
            tool_call_parser=HybridToolCallParser(),
        ),
    }


STRATEGIES = _build_strategies()

# Ordered by specificity: more specific names first
_MODEL_DETECTION_ORDER = ["qwen2.5", "qwen3", "mistral", "phi", "llama"]

_NATIVE_KEYWORDS = ["gpt", "claude", "openai"]


def get_model_strategy(
    model_path: str | None = None,
    tool_format: str | None = None,
) -> ModelStrategy:
    """Get the appropriate model strategy.

    Args:
        model_path: Path or identifier for the model, used for auto-detection.
        tool_format: Explicit format override ('qwen', 'simplified', 'native').
                     If set (and not 'auto'), overrides auto-detection.
    """
    from zikos.config import settings

    if tool_format is None:
        tool_format = settings.llm_tool_format

    if model_path is None:
        model_path = settings.llm_model_path

    # Explicit format selection
    if tool_format and tool_format != "auto":
        if tool_format == "qwen":
            return _copy_strategy(STRATEGIES["qwen2.5"])
        elif tool_format == "simplified":
            return _copy_strategy(STRATEGIES["default"])
        elif tool_format == "native":
            return _copy_strategy(STRATEGIES["native"])

    # Auto-detect from model path
    if model_path:
        name = model_path.lower()

        for key in _MODEL_DETECTION_ORDER:
            if key in name:
                return _copy_strategy(STRATEGIES[key])

        if any(kw in name for kw in _NATIVE_KEYWORDS):
            return _copy_strategy(STRATEGIES["native"])

    return _copy_strategy(STRATEGIES["default"])


def _copy_strategy(s: ModelStrategy) -> ModelStrategy:
    """Return a shallow copy so callers can't mutate the registry."""
    return ModelStrategy(
        tool_provider=s.tool_provider,
        tool_call_parser=s.tool_call_parser,
        sampling=SamplingParams(s.sampling.temperature, s.sampling.top_p, s.sampling.top_k),
        thinking=ThinkingConfig(
            s.thinking.enabled, s.thinking.prompt_suffix, s.thinking.max_tokens
        ),
        preferred_backend=s.preferred_backend,
    )
