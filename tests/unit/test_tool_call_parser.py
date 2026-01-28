"""Tests for ToolCallParser implementations"""

import json
from unittest.mock import patch

import pytest

from zikos.services.llm_orchestration.tool_call_parser import (
    HybridToolCallParser,
    NativeToolCallParser,
    QwenToolCallParser,
    SimplifiedToolCallParser,
    get_tool_call_parser,
)


class TestQwenToolCallParser:
    """Tests for QwenToolCallParser"""

    def test_parse_tool_calls_native_format(self):
        """Test parsing native tool calls format"""
        parser = QwenToolCallParser()
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
        parser = QwenToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = "Test response"

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_parse_qwen_format(self):
        """Test parsing Qwen XML tool call format"""
        parser = QwenToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = 'Here is my response <tool_call>{"name": "analyze_tempo", "arguments": {"audio_file_id": "test.wav"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "analyze_tempo"
        assert "call_qwen_" in result[0]["id"]

    def test_parse_qwen_multiple(self):
        """Test parsing multiple Qwen tool calls"""
        parser = QwenToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call><tool_call>{"name": "detect_pitch", "arguments": {}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 2
        assert result[0]["function"]["name"] == "analyze_tempo"
        assert result[1]["function"]["name"] == "detect_pitch"

    def test_parse_qwen_invalid_json(self):
        """Test parsing Qwen tool call with invalid JSON"""
        parser = QwenToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {invalid json}</tool_call>'

        with patch("zikos.services.llm_orchestration.tool_call_parser.settings") as mock_settings:
            mock_settings.debug_tool_calls = False
            result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_parse_qwen_fix_json_newlines(self):
        """Test parsing Qwen tool call with unescaped newlines"""
        parser = QwenToolCallParser()
        message_obj = {"content": "Test response"}
        raw_content = '<tool_call>{"name": "validate_midi", "arguments": {"midi_text": "Note C4\nNote D4"}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert result[0]["function"]["name"] == "validate_midi"

    def test_strip_tool_call_tags(self):
        """Test stripping tool call tags from content"""
        parser = QwenToolCallParser()
        content = 'Here is my response <tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call> and more text'

        result = parser.strip_tool_call_tags(content)

        assert "<tool_call>" not in result
        assert "Here is my response" in result
        assert "and more text" in result

    def test_fix_json_string_escapes_newlines(self):
        """Test _fix_json_string escapes newlines properly"""
        parser = QwenToolCallParser()
        json_str = '{"text": "line1\nline2"}'

        result = parser._fix_json_string(json_str)

        assert "\\n" in result

    def test_fix_json_string_escapes_tabs(self):
        """Test _fix_json_string escapes tabs properly"""
        parser = QwenToolCallParser()
        json_str = '{"text": "col1\tcol2"}'

        result = parser._fix_json_string(json_str)

        assert "\\t" in result


class TestSimplifiedToolCallParser:
    """Tests for SimplifiedToolCallParser"""

    def test_parse_simplified_basic(self):
        """Test parsing basic simplified tool call"""
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="some_tool">
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        args = json.loads(result[0]["function"]["arguments"])
        assert args == {}

    def test_parse_simplified_with_thinking(self):
        """Test that tool calls work alongside thinking tags"""
        parser = SimplifiedToolCallParser()
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
        parser = SimplifiedToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="request_audio_recording">
prompt: Play at 12:30 tempo marking
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        args = json.loads(result[0]["function"]["arguments"])
        assert args["prompt"] == "Play at 12:30 tempo marking"

    def test_strip_tool_call_tags_simplified(self):
        """Test stripping simplified tool call tags from content"""
        parser = SimplifiedToolCallParser()
        content = """Here is my response
<tool name="request_audio_recording">
prompt: Play a scale
</tool>
and more text"""

        result = parser.strip_tool_call_tags(content)

        assert "<tool" not in result
        assert "Here is my response" in result
        assert "and more text" in result

    def test_parse_key_value_empty_value(self):
        """Test parsing key with empty value"""
        parser = SimplifiedToolCallParser()
        result = parser._parse_key_value_params("key:")

        assert result.get("key") == ""

    def test_parse_key_value_whitespace(self):
        """Test parsing handles whitespace in values correctly"""
        parser = SimplifiedToolCallParser()
        result = parser._parse_key_value_params("key:  value with spaces  ")

        assert result.get("key") == "value with spaces"


class TestNativeToolCallParser:
    """Tests for NativeToolCallParser"""

    def test_parse_native_format_only(self):
        """Test that native parser only uses message.tool_calls"""
        parser = NativeToolCallParser()
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

        result = parser.parse_tool_calls(message_obj, "Test response")

        assert len(result) == 1
        assert result[0]["function"]["name"] == "analyze_tempo"

    def test_parse_ignores_content(self):
        """Test that native parser ignores tool calls in content"""
        parser = NativeToolCallParser()
        message_obj = {"content": ""}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert result == []

    def test_strip_tool_call_tags(self):
        """Test that strip returns content unchanged"""
        parser = NativeToolCallParser()
        content = "Some content with no changes needed"

        result = parser.strip_tool_call_tags(content)

        assert result == content


class TestHybridToolCallParser:
    """Tests for HybridToolCallParser"""

    def test_parse_simplified_first(self):
        """Test that hybrid parser tries simplified format first"""
        parser = HybridToolCallParser()
        message_obj = {"content": ""}
        raw_content = """<tool name="request_audio_recording">
prompt: Play a scale
</tool>"""

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert "call_" in result[0]["id"]  # Simplified format ID

    def test_parse_falls_back_to_qwen(self):
        """Test that hybrid parser falls back to Qwen format"""
        parser = HybridToolCallParser()
        message_obj = {"content": ""}
        raw_content = '<tool_call>{"name": "analyze_tempo", "arguments": {}}</tool_call>'

        result = parser.parse_tool_calls(message_obj, raw_content)

        assert len(result) == 1
        assert "call_qwen_" in result[0]["id"]

    def test_strip_both_formats(self):
        """Test stripping both simplified and Qwen tags"""
        parser = HybridToolCallParser()
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


class TestGetToolCallParser:
    """Tests for get_tool_call_parser factory"""

    def test_get_qwen_parser(self):
        """Test getting Qwen parser"""
        parser = get_tool_call_parser("qwen")
        assert isinstance(parser, QwenToolCallParser)

    def test_get_simplified_parser(self):
        """Test getting simplified parser"""
        parser = get_tool_call_parser("simplified")
        assert isinstance(parser, SimplifiedToolCallParser)

    def test_get_native_parser(self):
        """Test getting native parser"""
        parser = get_tool_call_parser("native")
        assert isinstance(parser, NativeToolCallParser)

    def test_get_auto_parser(self):
        """Test getting auto (hybrid) parser"""
        parser = get_tool_call_parser("auto")
        assert isinstance(parser, HybridToolCallParser)

    def test_default_to_hybrid(self):
        """Test that unknown format defaults to hybrid"""
        parser = get_tool_call_parser("unknown")
        assert isinstance(parser, HybridToolCallParser)
