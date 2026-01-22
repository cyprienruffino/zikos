"""Tool provider implementations"""

from zikos.services.tool_provider import ToolProvider
from zikos.services.tool_providers.structured_tool_provider import StructuredToolProvider
from zikos.services.tool_providers.xml_tool_provider import XMLToolProvider


def get_tool_provider(model_path: str | None = None) -> ToolProvider:
    """Detect model type and return appropriate tool provider"""
    if model_path is None:
        from zikos.config import settings

        model_path = settings.llm_model_path

    if model_path is None:
        return XMLToolProvider()

    model_name_lower = model_path.lower()

    if "qwen" in model_name_lower:
        return XMLToolProvider()
    elif any(x in model_name_lower for x in ["gpt", "claude", "openai"]):
        return StructuredToolProvider()
    else:
        return XMLToolProvider()
