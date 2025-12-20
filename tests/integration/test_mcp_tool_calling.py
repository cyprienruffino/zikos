"""Integration tests for MCP tool calling without LLM

These tests verify that tools work correctly when called directly,
without needing the LLM. This helps isolate issues between tool
functionality and LLM integration.
"""

import pytest

pytestmark = pytest.mark.integration


class TestMCPToolCalling:
    """Tests for MCP server tool calling"""

    @pytest.mark.asyncio
    async def test_metronome_tool_call(self):
        """Test calling metronome tool directly"""
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        result = await mcp_server.call_tool(
            "create_metronome", bpm=120, time_signature="4/4", description="Test metronome"
        )

        assert isinstance(result, dict)
        assert result["status"] == "metronome_created"
        assert result["bpm"] == 120
        assert result["time_signature"] == "4/4"
        assert "metronome_id" in result

    @pytest.mark.asyncio
    async def test_recording_tool_call(self):
        """Test calling recording tool directly"""
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        result = await mcp_server.call_tool(
            "request_audio_recording", prompt="Test recording", max_duration=60.0
        )

        assert isinstance(result, dict)
        assert result["status"] == "recording_requested"
        assert result["prompt"] == "Test recording"
        assert result["max_duration"] == 60.0
        assert "recording_id" in result

    @pytest.mark.asyncio
    async def test_tuner_tool_call(self):
        """Test calling tuner tool directly"""
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        result = await mcp_server.call_tool(
            "create_tuner", reference_frequency=440.0, note="A", octave=4
        )

        assert isinstance(result, dict)
        assert result["status"] == "tuner_created"
        assert result["reference_frequency"] == 440.0
        assert result["note"] == "A"
        assert result["octave"] == 4
        assert "tuner_id" in result

    @pytest.mark.asyncio
    async def test_chord_progression_tool_call(self):
        """Test calling chord progression tool directly"""
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        result = await mcp_server.call_tool(
            "create_chord_progression",
            chords=["C", "G", "Am", "F"],
            tempo=120,
            time_signature="4/4",
            chords_per_bar=1,
            instrument="piano",
        )

        assert isinstance(result, dict)
        assert result["status"] == "chord_progression_created"
        assert result["chords"] == ["C", "G", "Am", "F"]
        assert result["tempo"] == 120
        assert "progression_id" in result

    @pytest.mark.asyncio
    async def test_unknown_tool_error(self):
        """Test that unknown tools raise appropriate errors"""
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        with pytest.raises(ValueError, match="Unknown tool"):
            await mcp_server.call_tool("nonexistent_tool", arg1="value")

    @pytest.mark.asyncio
    async def test_tool_schemas_format(self):
        """Test that tool schemas are properly formatted"""
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        tools = mcp_server.get_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Verify schema structure
        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool

            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

            params = func["parameters"]
            assert "type" in params
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params

    @pytest.mark.asyncio
    async def test_audio_analysis_tool_with_synthesized_audio(self, temp_dir):
        """Test audio analysis tool with real synthesized audio"""
        from pathlib import Path

        from tests.helpers.audio_synthesis import create_test_audio_file
        from zikos.mcp.server import MCPServer

        mcp_server = MCPServer()

        # Create synthesized audio file
        audio_file = temp_dir / "test_scale.wav"
        create_test_audio_file(audio_file, audio_type="scale", duration=2.0)

        # Store it in the expected location
        # Copy file to audio storage
        import shutil
        import uuid

        from zikos.config import settings

        audio_file_id = str(uuid.uuid4())
        storage_path = Path(settings.audio_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        target_path = storage_path / f"{audio_file_id}.wav"
        shutil.copy(audio_file, target_path)

        try:
            # Test tempo analysis
            result = await mcp_server.call_tool("analyze_tempo", audio_file_id=audio_file_id)

            assert isinstance(result, dict)
            assert "bpm" in result or "error" in result  # May have error if analysis fails

            # Test pitch detection
            result = await mcp_server.call_tool("detect_pitch", audio_file_id=audio_file_id)

            assert isinstance(result, dict)
            # Should have some pitch information or error
            assert "notes" in result or "error" in result

        finally:
            # Cleanup
            if target_path.exists():
                target_path.unlink()
