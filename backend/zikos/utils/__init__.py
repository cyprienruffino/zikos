"""Utility functions"""

from zikos.utils.context_length import detect_context_length
from zikos.utils.gpu import detect_gpu, get_optimal_gpu_layers
from zikos.utils.token_budget import (
    calculate_available_tokens,
    calculate_reserve_tokens,
    get_max_tokens_for_preparation,
    get_max_tokens_for_validation,
)

__all__ = [
    "detect_context_length",
    "detect_gpu",
    "get_optimal_gpu_layers",
    "calculate_reserve_tokens",
    "calculate_available_tokens",
    "get_max_tokens_for_preparation",
    "get_max_tokens_for_validation",
]
