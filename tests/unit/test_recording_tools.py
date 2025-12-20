"""Tests for recording tools"""

from unittest.mock import patch

import pytest

from zikos.mcp.tools.interaction.recording import RecordingTools


@pytest.fixture
def recording_tools():
    """Create RecordingTools instance"""
    return RecordingTools()


class TestRecordingTools:
    """Tests for RecordingTools"""

    def test_get_tool_schemas(self, recording_tools):
        """Test getting tool schemas"""
        schemas = recording_tools.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 1

        schema = schemas[0]
        assert schema["function"]["name"] == "request_audio_recording"
        assert "prompt" in schema["function"]["parameters"]["properties"]
        assert "max_duration" in schema["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_request_audio_recording(self, recording_tools):
        """Test requesting audio recording"""
        result = await recording_tools.request_audio_recording("Play C major scale", 60.0)

        assert result["status"] == "recording_requested"
        assert result["prompt"] == "Play C major scale"
        assert result["max_duration"] == 60.0
        assert "recording_id" in result
        assert isinstance(result["recording_id"], str)
        assert len(result["recording_id"]) > 0

    @pytest.mark.asyncio
    async def test_request_audio_recording_default_duration(self, recording_tools):
        """Test requesting audio recording with default duration via call_tool"""
        result = await recording_tools.call_tool("request_audio_recording", prompt="Play a scale")

        assert result["max_duration"] == 30.0

    @pytest.mark.asyncio
    async def test_call_tool_request_audio_recording(self, recording_tools):
        """Test call_tool for request_audio_recording"""
        result = await recording_tools.call_tool(
            "request_audio_recording",
            prompt="Test prompt",
            max_duration=30.0,
        )

        assert result["status"] == "recording_requested"
        assert result["prompt"] == "Test prompt"
        assert result["max_duration"] == 30.0

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, recording_tools):
        """Test call_tool with unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await recording_tools.call_tool("unknown_tool", arg1="test")
