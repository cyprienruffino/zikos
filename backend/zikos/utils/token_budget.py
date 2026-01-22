"""Utilities for calculating token budgets based on context window size"""

import logging

from zikos.constants import LLM

_logger = logging.getLogger(__name__)


def calculate_reserve_tokens(context_window: int) -> int:
    """Calculate reserve tokens proportional to context window

    Uses 10% of context window, with minimum of 200 tokens for very small windows.

    Args:
        context_window: The actual context window size in tokens

    Returns:
        Number of tokens to reserve for response generation and safety margin
    """
    # Use 10% of context window, minimum 200 tokens
    reserve = max(int(context_window * 0.1), 200)

    # For very large context windows, cap at reasonable maximum
    # (e.g., 32K window = 3.2K reserve, 128K window = 12.8K reserve)
    # No cap needed - 10% is reasonable for any size

    return reserve


def calculate_available_tokens(
    context_window: int,
    system_prompt_tokens: int,
    tool_schemas_tokens: int = 0,
) -> int:
    """Calculate available tokens for conversation history

    Args:
        context_window: The actual context window size in tokens
        system_prompt_tokens: Size of system prompt in tokens
        tool_schemas_tokens: Size of tool schemas if injected (optional)

    Returns:
        Number of tokens available for conversation history
    """
    reserve = calculate_reserve_tokens(context_window)

    available = context_window - system_prompt_tokens - tool_schemas_tokens - reserve

    # Ensure we don't return negative (shouldn't happen with proper sizing)
    if available < 0:
        _logger.warning(
            f"Available tokens is negative ({available}). "
            f"Context window: {context_window}, System prompt: {system_prompt_tokens}, "
            f"Tool schemas: {tool_schemas_tokens}, Reserve: {reserve}. "
            "Consider reducing system prompt size or tool schemas."
        )
        # Return at least 100 tokens to allow some conversation
        return max(available, 100)

    return available


def get_max_tokens_for_preparation(context_window: int) -> int:
    """Get maximum tokens to use for message preparation

    This should be used instead of the hardcoded LLM.MAX_TOKENS_PREPARE_MESSAGES
    when preparing messages for a specific model.

    Args:
        context_window: The actual context window size in tokens

    Returns:
        Maximum tokens to use for message preparation (context window minus small safety margin)
    """
    # Use 95% of context window to leave small safety margin
    return int(context_window * 0.95)


def get_max_tokens_for_validation(context_window: int) -> int:
    """Get maximum tokens to use for validation

    This should be used instead of the hardcoded LLM.MAX_TOKENS_SAFETY_CHECK
    when validating token limits.

    Args:
        context_window: The actual context window size in tokens

    Returns:
        Maximum tokens allowed (context window minus reserve)
    """
    reserve = calculate_reserve_tokens(context_window)
    return context_window - reserve
