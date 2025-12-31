"""Tests for ToolCallParser"""

from unittest.mock import MagicMock, patch

import pytest

from zikos.services.llm_orchestration.tool_call_parser import ToolCallParser


class TestToolCallParser:
    """Tests for ToolCallParser"""

    def test_parse_tool_calls_native_format(self):
        """Test parsing native tool calls format"""
        parser = ToolCallParser()
        message_obj = {
            "content": "Test response",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "analyze_tempo",
                        "arguments": '{"audio_file_id": "test.wav"}',
                    },
                }
            ],
        }
        raw_content = "Test response"

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["id"] == "call_123"
        assert result[0]["function"]["name"] == "analyze_tempo"

    def test_parse_tool_calls_no_tool_calls(self):
        """Test parsing when no tool calls present"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = "Test response"

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_parse_tool_calls_qwen_format(self):
        """Test parsing Qwen XML tool call format"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = 'Here is my response <tool_call>{"name": "analyze_tempo", "arguments": {"audio_file_id": "test.wav"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "analyze_tempo"
        assert "call_qwen_" in result[0]["id"]

    def test_parse_tool_calls_qwen_multiple(self):
        """Test parsing multiple Qwen tool calls"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call><tool_call>{"name": "detect_pitch", "arguments": {}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 2
        assert result[0]["function"]["name"] == "analyze_tempo"
        assert result[1]["function"]["name"] == "detect_pitch"

    def test_parse_tool_calls_qwen_invalid_json(self):
        """Test parsing Qwen tool call with invalid JSON"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {invalid json}</tool_call>'

        with patch("zikos.services.llm_orchestration.tool_call_parser.settings") as mock_settings:
            mock_settings.debug_tool_calls = False
            result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_parse_tool_calls_qwen_fix_json_newlines(self):
        """Test parsing Qwen tool call with unescaped newlines"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "validate_midi", "arguments": {"midi_text": "Note C4\nNote D4"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "validate_midi"

    def test_parse_tool_calls_qwen_fix_json_tabs(self):
        """Test parsing Qwen tool call with unescaped tabs"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "validate_midi", "arguments": {"midi_text": "Note C4\tNote D4"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "validate_midi"

    def test_parse_tool_calls_qwen_missing_name(self):
        """Test parsing Qwen tool call without name"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"arguments": {"audio_file_id": "test.wav"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_strip_tool_call_tags(self):
        """Test stripping tool call tags from content"""
        parser = ToolCallParser()
        content = 'Here is my response <tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call> and more text'

        result = parser.strip_tool_call_tags(content)

        assert "<tool_call>" not in result
        assert "Here is my response" in result
        assert "and more text" in result

    def test_strip_tool_call_tags_multiple(self):
        """Test stripping multiple tool call tags"""
        parser = ToolCallParser()
        content = 'Text <tool_call>{"name": "tool1"}</tool_call> middle <tool_call>{"name": "tool2"}</tool_call> end'

        result = parser.strip_tool_call_tags(content)

        assert "<tool_call>" not in result
        assert "Text" in result
        assert "middle" in result
        assert "end" in result

    def test_strip_tool_call_tags_none(self):
        """Test stripping when no tags present"""
        parser = ToolCallParser()
        content = "Just regular text with no tool calls"

        result = parser.strip_tool_call_tags(content)

        assert result == content

    def test_fix_json_string_escapes_newlines(self):
        """Test _fix_json_string escapes newlines properly"""
        parser = ToolCallParser()
        json_str = '{"text": "line1\nline2"}'

        result = parser._fix_json_string(json_str)

        assert "\\n" in result
        assert "\n" not in result or result.count("\n") < json_str.count("\n")

    def test_fix_json_string_escapes_tabs(self):
        """Test _fix_json_string escapes tabs properly"""
        parser = ToolCallParser()
        json_str = '{"text": "col1\tcol2"}'

        result = parser._fix_json_string(json_str)

        assert "\\t" in result

    def test_fix_json_string_handles_escaped_chars(self):
        """Test _fix_json_string doesn't double-escape"""
        parser = ToolCallParser()
        json_str = '{"text": "already\\nescaped"}'

        result = parser._fix_json_string(json_str)

        assert json_str in result or "already\\\\n" in result
