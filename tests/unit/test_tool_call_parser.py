"""Tests for ToolCallParser"""

import json
from unittest.mock import patch

import pytest

from zikos.services.llm_orchestration.tool_call_parser import ToolCallParser


class TestToolCallParser:
    """Tests for ToolCallParser"""

    # === Native format tests ===

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

    # === Simplified XML format tests ===

    def test_parse_simplified_basic(self):
        """Test parsing basic simplified tool call"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """Here is my response
<tool name="request_audio_recording">
prompt: Play a C major scale
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "request_audio_recording"
        args = json.loads(result[0]["function"]["arguments"])
        assert args["prompt"] == "Play a C major scale"

    def test_parse_simplified_multiple_params(self):
        """Test parsing simplified format with multiple parameters"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="create_metronome">
bpm: 120
time_signature: 4/4
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        args = json.loads(result[0]["function"]["arguments"])
        assert args["bpm"] == 120
        assert args["time_signature"] == "4/4"

    def test_parse_simplified_numeric_conversion(self):
        """Test that numeric values are converted properly"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="create_metronome">
bpm: 90
max_duration: 30.5
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        args = json.loads(result[0]["function"]["arguments"])
        assert args["bpm"] == 90
        assert isinstance(args["bpm"], int)
        assert args["max_duration"] == 30.5
        assert isinstance(args["max_duration"], float)

    def test_parse_simplified_boolean_conversion(self):
        """Test that boolean-like values are converted properly"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="some_tool">
enabled: true
disabled: false
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        args = json.loads(result[0]["function"]["arguments"])
        assert args["enabled"] is True
        assert args["disabled"] is False

    def test_parse_simplified_multiline_value(self):
        """Test parsing simplified format with multiline value"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="validate_midi">
midi_text: |
  MFile 1 1 480
  MTrk
  0 Tempo 500000
  TrkEnd
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        args = json.loads(result[0]["function"]["arguments"])
        assert "MFile 1 1 480" in args["midi_text"]
        assert "MTrk" in args["midi_text"]
        assert "TrkEnd" in args["midi_text"]

    def test_parse_simplified_multiline_preserves_structure(self):
        """Test that multiline values preserve newlines"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="validate_midi">
midi_text: |
  Line1
  Line2
  Line3
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        args = json.loads(result[0]["function"]["arguments"])
        lines = args["midi_text"].split("\n")
        assert len(lines) == 3

    def test_parse_simplified_multiple_tools(self):
        """Test parsing multiple simplified tool calls"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="request_audio_recording">
prompt: Play something
</tool>
Some text between
<tool name="create_metronome">
bpm: 100
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 2
        assert result[0]["function"]["name"] == "request_audio_recording"
        assert result[1]["function"]["name"] == "create_metronome"

    def test_parse_simplified_no_params(self):
        """Test parsing simplified format with no parameters"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="some_tool">
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        args = json.loads(result[0]["function"]["arguments"])
        assert args == {}

    def test_parse_simplified_with_thinking(self):
        """Test that tool calls work alongside thinking tags"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<thinking>User wants to practice, I should request a recording</thinking>
<tool name="request_audio_recording">
prompt: Play a scale
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "request_audio_recording"

    def test_parse_simplified_value_with_colon(self):
        """Test parsing value that contains colons"""
        parser = ToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="request_audio_recording">
prompt: Play at 12:30 tempo marking
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        args = json.loads(result[0]["function"]["arguments"])
        assert args["prompt"] == "Play at 12:30 tempo marking"

    # === Legacy Qwen format tests (backwards compatibility) ===

    def test_parse_tool_calls_legacy_format(self):
        """Test parsing legacy Qwen XML tool call format"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = 'Here is my response <tool_call>{"name": "analyze_tempo", "arguments": {"audio_file_id": "test.wav"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "analyze_tempo"
        assert "call_legacy_" in result[0]["id"]

    def test_parse_tool_calls_legacy_multiple(self):
        """Test parsing multiple legacy tool calls"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call><tool_call>{"name": "detect_pitch", "arguments": {}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 2
        assert result[0]["function"]["name"] == "analyze_tempo"
        assert result[1]["function"]["name"] == "detect_pitch"

    def test_parse_tool_calls_legacy_invalid_json(self):
        """Test parsing legacy tool call with invalid JSON"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {invalid json}</tool_call>'

        with patch("zikos.services.llm_orchestration.tool_call_parser.settings") as mock_settings:
            mock_settings.debug_tool_calls = False
            result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_parse_tool_calls_legacy_fix_json_newlines(self):
        """Test parsing legacy tool call with unescaped newlines"""
        parser = ToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "validate_midi", "arguments": {"midi_text": "Note C4\nNote D4"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "validate_midi"

    # === Strip tool call tags tests ===

    def test_strip_tool_call_tags_simplified(self):
        """Test stripping simplified tool call tags from content"""
        parser = ToolCallParser()
        content = """Here is my response
<tool name="request_audio_recording">
prompt: Play a scale
</tool>
and more text"""

        result = parser.strip_tool_call_tags(content)

        assert "<tool" not in result
        assert "Here is my response" in result
        assert "and more text" in result

    def test_strip_tool_call_tags_legacy(self):
        """Test stripping legacy tool call tags from content"""
        parser = ToolCallParser()
        content = 'Here is my response <tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call> and more text'

        result = parser.strip_tool_call_tags(content)

        assert "<tool_call>" not in result
        assert "Here is my response" in result
        assert "and more text" in result

    def test_strip_tool_call_tags_mixed(self):
        """Test stripping both simplified and legacy tags"""
        parser = ToolCallParser()
        content = """Text
<tool name="tool1">
param: value
</tool>
middle
<tool_call>{"name": "tool2"}</tool_call>
end"""

        result = parser.strip_tool_call_tags(content)

        assert "<tool" not in result
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

    # === Key-value parsing edge cases ===

    def test_parse_key_value_empty_value(self):
        """Test parsing key with empty value"""
        parser = ToolCallParser()
        result = parser._parse_key_value_params("key:")

        assert result.get("key") == ""

    def test_parse_key_value_whitespace(self):
        """Test parsing handles whitespace in values correctly"""
        parser = ToolCallParser()
        result = parser._parse_key_value_params("key:  value with spaces  ")

        assert result.get("key") == "value with spaces"

    # === JSON fix helper tests ===

    def test_fix_json_string_escapes_newlines(self):
        """Test _fix_json_string escapes newlines properly"""
        parser = ToolCallParser()
        json_str = '{"text": "line1\nline2"}'

        result = parser._fix_json_string(json_str)

        assert "\\n" in result

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

        # Should not double-escape
        assert "\\\\n" not in result or json_str == result
