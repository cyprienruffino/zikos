"""Tests for ThinkingExtractor"""

import pytest

from zikos.services.llm_orchestration.thinking_extractor import ThinkingExtractor


class TestThinkingExtractor:
    """Tests for ThinkingExtractor"""

    def test_extract_no_thinking(self):
        """Test extracting thinking when no thinking tags present"""
        content = "This is a normal response without thinking tags."

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert cleaned == content
        assert thinking == ""

    def test_extract_with_thinking(self):
        """Test extracting thinking when thinking tags present"""
        content = "<thinking>I need to analyze this carefully.</thinking>Here is my response."

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert "thinking" not in cleaned.lower()
        assert "Here is my response" in cleaned
        assert "I need to analyze this carefully" in thinking

    def test_extract_multiple_thinking(self):
        """Test extracting multiple thinking blocks"""
        content = "<thinking>First thought</thinking>Some text<thinking>Second thought</thinking>More text"

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert "thinking" not in cleaned.lower()
        assert "First thought" in thinking
        assert "Second thought" in thinking
        assert "\n\n" in thinking

    def test_extract_thinking_multiline(self):
        """Test extracting thinking with multiline content"""
        content = """<thinking>
I need to think about this.
This is a complex problem.
</thinking>
Here is my answer."""

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert "Here is my answer" in cleaned
        assert "I need to think about this" in thinking
        assert "This is a complex problem" in thinking

    def test_extract_none_content(self):
        """Test extracting thinking with None content"""
        cleaned, thinking = ThinkingExtractor.extract(None)

        assert cleaned == ""
        assert thinking == ""

    def test_extract_empty_content(self):
        """Test extracting thinking with empty content"""
        cleaned, thinking = ThinkingExtractor.extract("")

        assert cleaned == ""
        assert thinking == ""

    def test_extract_thinking_only(self):
        """Test extracting when content is only thinking"""
        content = "<thinking>Just thinking, no response</thinking>"

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert cleaned == ""
        assert thinking == "Just thinking, no response"

    def test_lone_closing_tag_treats_prefix_as_thinking(self):
        """llama.cpp's Qwen3 template emits the opening <think> in the prompt,
        so responses can arrive with only a closing tag: everything before it
        is thinking."""
        content = "Let me reason about scales here.\n</think>\nPlay a C major scale."

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert cleaned == "Play a C major scale."
        assert "reason about scales" in thinking
        assert "</think>" not in cleaned

    def test_lone_closing_thinking_tag(self):
        content = "hidden reasoning</thinking>visible answer"

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert cleaned == "visible answer"
        assert thinking == "hidden reasoning"

    def test_mismatched_tags_not_paired(self):
        """<think>...</thinking> is not a matched pair; content is still
        separated into thinking and visible text without leaking tags."""
        content = "<think>mismatched reasoning</thinking>final answer"

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert cleaned == "final answer"
        assert "mismatched reasoning" in thinking
        assert "<think>" not in cleaned
        assert "</thinking>" not in cleaned

    def test_pair_plus_lone_closer(self):
        content = "prefix</think>middle<think>pair</think>end"

        cleaned, thinking = ThinkingExtractor.extract(content)

        assert "prefix" in thinking
        assert "pair" in thinking
        assert "middle" in cleaned
        assert "end" in cleaned
