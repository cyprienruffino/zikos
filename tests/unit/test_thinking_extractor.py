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
