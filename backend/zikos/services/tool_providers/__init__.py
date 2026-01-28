"""Tool provider implementations"""

from zikos.services.tool_provider import ToolProvider
from zikos.services.tool_providers.qwen_tool_provider import QwenToolProvider
from zikos.services.tool_providers.simplified_tool_provider import SimplifiedToolProvider
from zikos.services.tool_providers.structured_tool_provider import StructuredToolProvider

# Keep XMLToolProvider as alias for backwards compatibility
XMLToolProvider = SimplifiedToolProvider


def get_tool_provider(
    tool_format: str | None = None, model_path: str | None = None
) -> ToolProvider:
    """Get appropriate tool provider based on config and model

    Args:
        tool_format: One of 'auto', 'qwen', 'simplified', 'native'.
                    If None, reads from settings.
        model_path: Path to model file, used for auto-detection.
                   If None, reads from settings.

    Returns:
        Appropriate ToolProvider instance
    """
    from zikos.config import settings

    if tool_format is None:
        tool_format = settings.llm_tool_format

    if model_path is None:
        model_path = settings.llm_model_path

    # Direct format selection
    if tool_format == "qwen":
        return QwenToolProvider()
    elif tool_format == "simplified":
        return SimplifiedToolProvider()
    elif tool_format == "native":
        return StructuredToolProvider()

    # Auto-detect from model name
    if model_path:
        model_name_lower = model_path.lower()

        if "qwen" in model_name_lower:
            return QwenToolProvider()
        elif any(x in model_name_lower for x in ["gpt", "claude", "openai"]):
            return StructuredToolProvider()
        elif any(x in model_name_lower for x in ["phi", "mistral", "llama"]):
            # These models work better with simplified format
            return SimplifiedToolProvider()

    # Default to simplified for local models (most forgiving)
    return SimplifiedToolProvider()


def detect_tool_format_from_metadata(metadata: dict) -> str:
    """Detect tool format from model metadata (e.g., GGUF metadata)

    Args:
        metadata: Model metadata dictionary

    Returns:
        Tool format string: 'qwen', 'simplified', or 'native'
    """
    model_name = metadata.get("general.name", "").lower()
    base_model = metadata.get("general.base_model.0.name", "").lower()

    # Check for Qwen
    if "qwen" in model_name or "qwen" in base_model:
        return "qwen"

    # Check for models that typically have good native support
    if any(x in model_name for x in ["gpt", "claude"]):
        return "native"

    # Default to simplified for safety
    return "simplified"
