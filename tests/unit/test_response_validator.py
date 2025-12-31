"""Tests for ResponseValidator"""

import pytest

from zikos.constants import LLM
from zikos.services.llm_orchestration.response_validator import ResponseValidator


class TestResponseValidator:
    """Tests for ResponseValidator"""

    @pytest.fixture
    def validator(self):
        """Create ResponseValidator instance"""
        return ResponseValidator()

    def test_validate_token_limit_under_limit(self, validator):
        """Test token limit validation when under limit"""
        messages = [{"role": "user", "content": "Short message"}]

        result = validator.validate_token_limit(messages)

        assert result is None

    def test_validate_token_limit_over_limit(self, validator):
        """Test token limit validation when over limit"""
        long_content = "word " * (LLM.MAX_TOKENS_SAFETY_CHECK + 100)
        messages = [{"role": "user", "content": long_content}]

        result = validator.validate_token_limit(messages)

        assert result is not None
        assert result["error_type"] == "token_limit"
        assert "exceeds token limit" in result["error_details"].lower()

    def test_validate_token_limit_multiple_messages(self, validator):
        """Test token limit validation with multiple messages"""
        messages = [
            {"role": "user", "content": "word " * (LLM.MAX_TOKENS_SAFETY_CHECK // 3)},
            {"role": "assistant", "content": "word " * (LLM.MAX_TOKENS_SAFETY_CHECK // 3)},
            {"role": "user", "content": "word " * (LLM.MAX_TOKENS_SAFETY_CHECK // 2)},
        ]

        result = validator.validate_token_limit(messages)

        assert result is not None
        assert result["error_type"] == "token_limit"

    def test_validate_response_content_empty(self, validator):
        """Test response content validation with empty content"""
        result = validator.validate_response_content("")

        assert result is None

    def test_validate_response_content_normal(self, validator):
        """Test response content validation with normal content"""
        content = "This is a normal response with reasonable length and variety of words."

        result = validator.validate_response_content(content)

        assert result is None

    def test_validate_response_content_too_long(self, validator):
        """Test response content validation with too many words"""
        content = "word " * (LLM.MAX_WORDS_RESPONSE + 1)

        result = validator.validate_response_content(content)

        assert result is not None
        assert result["error_type"] == "response_too_long"
        assert "exceeds maximum word count" in result["error_details"].lower()

    def test_validate_response_content_repetitive(self, validator):
        """Test response content validation with repetitive words"""
        content = "word " * 100

        result = validator.validate_response_content(content)

        assert result is not None
        assert result["error_type"] == "repetitive_output"
        assert "unique word ratio" in result["error_details"].lower()

    def test_validate_response_content_single_chars(self, validator):
        """Test response content validation with too many single characters"""
        # Create content with many single chars but enough unique words to pass repetitive check
        unique_words = " ".join(f"word{i}" for i in range(60))
        single_chars = "a b c d e f g h i j " * 10
        content = unique_words + " " + single_chars

        result = validator.validate_response_content(content)

        assert result is not None
        assert result["error_type"] == "invalid_response_pattern"
        assert "single characters" in result["error_details"].lower()

    def test_validate_response_content_short_repetitive(self, validator):
        """Test response content validation with short repetitive content (should pass)"""
        content = "word word word"

        result = validator.validate_response_content(content)

        assert result is None

    def test_validate_tool_call_loops_under_limit(self, validator):
        """Test tool call loop validation when under limit"""
        result = validator.validate_tool_call_loops(5, ["tool1", "tool2", "tool3"])

        assert result is None

    def test_validate_tool_call_loops_over_consecutive_limit(self, validator):
        """Test tool call loop validation when over consecutive limit"""
        result = validator.validate_tool_call_loops(
            LLM.MAX_CONSECUTIVE_TOOL_CALLS + 1, ["tool1", "tool2"]
        )

        assert result is not None
        assert result["error_type"] == "too_many_tool_calls"
        assert "consecutive tool calls" in result["error_details"].lower()

    def test_validate_tool_call_loops_repetitive_pattern(self, validator):
        """Test tool call loop validation with repetitive pattern"""
        tool_name = "analyze_tempo"
        recent_calls = [tool_name] * LLM.REPETITIVE_PATTERN_THRESHOLD

        result = validator.validate_tool_call_loops(5, recent_calls)

        assert result is not None
        assert result["error_type"] == "repetitive_tool_calls"
        assert tool_name in result["error_details"]

    def test_validate_tool_call_loops_custom_max_consecutive(self, validator):
        """Test tool call loop validation with custom max consecutive"""
        custom_max = 10
        result = validator.validate_tool_call_loops(custom_max + 1, [], max_consecutive=custom_max)

        assert result is not None
        assert result["error_type"] == "too_many_tool_calls"

    def test_validate_tool_call_loops_repetitive_not_enough(self, validator):
        """Test tool call loop validation with repetitive but not enough calls"""
        tool_name = "analyze_tempo"
        recent_calls = [tool_name] * (LLM.REPETITIVE_PATTERN_THRESHOLD - 1)

        result = validator.validate_tool_call_loops(5, recent_calls)

        assert result is None
