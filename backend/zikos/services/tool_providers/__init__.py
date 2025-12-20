"""Tool provider implementations"""

from zikos.services.tool_provider import ToolProvider
from zikos.services.tool_providers.openai import OpenAIToolProvider
from zikos.services.tool_providers.qwen import QwenToolProvider


def get_tool_provider(model_path: str | None = None) -> ToolProvider:
    """Detect model type and return appropriate tool provider"""
    if model_path is None:
        from zikos.config import settings

        model_path = settings.llm_model_path

    if model_path is None:
        return QwenToolProvider()

    model_name_lower = model_path.lower()

    if "qwen" in model_name_lower:
        return QwenToolProvider()
    elif any(x in model_name_lower for x in ["gpt", "claude", "openai"]):
        return OpenAIToolProvider()
    else:
        return QwenToolProvider()
