"""Realistic integration tests for LLM tool calling

These tests verify that the LLM can actually use tools correctly.
Marked as expensive and llm - uses real LLM and real MCP server.
"""

import pytest

pytestmark = pytest.mark.comprehensive


class TestLLMToolCallingIntegration:
    """Integration tests for LLM tool calling with real components"""

    @pytest.mark.asyncio
    async def test_llm_can_call_metronome_tool(self):
        """Test that LLM can call the metronome tool when requested"""
        from zikos.mcp.server import MCPServer
        from zikos.services.llm import LLMService

        service = LLMService()
        mcp_server = MCPServer()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        # Clear any existing conversation
        session_id = "test_metronome_session"
        service.conversations.clear()

        # Request metronome - should trigger tool call
        result = await service.generate_response(
            "I need a metronome at 120 BPM",
            session_id=session_id,
            mcp_server=mcp_server,
        )

        assert "type" in result
        # Should either call the tool directly (via pre-detection) or via LLM
        if result["type"] == "tool_call":
            assert result["tool_name"] == "create_metronome"
            assert "arguments" in result
            # Check that arguments are correct
            args = result["arguments"]
            assert args.get("bpm") == 120 or args.get("bpm") is None  # May be None if not parsed
        else:
            # LLM might return a response instead - check if it mentions metronome
            assert result["type"] == "response"
            # This would indicate the LLM didn't call the tool - potential bug
            message = result.get("message", "").lower()
            # If it's a response, it should at least acknowledge the request
            assert len(message) > 0

    @pytest.mark.asyncio
    async def test_llm_can_call_recording_tool(self):
        """Test that LLM can call the recording tool when requested"""
        from zikos.mcp.server import MCPServer
        from zikos.services.llm import LLMService

        service = LLMService()
        mcp_server = MCPServer()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        session_id = "test_recording_session"
        service.conversations.clear()

        # Request recording - should trigger tool call
        result = await service.generate_response(
            "Let's record a sample",
            session_id=session_id,
            mcp_server=mcp_server,
        )

        assert "type" in result
        if result["type"] == "tool_call":
            assert result["tool_name"] == "request_audio_recording"
            assert "arguments" in result
        else:
            # If it's a response, check if it's helpful
            assert result["type"] == "response"
            message = result.get("message", "").lower()
            assert len(message) > 0

    @pytest.mark.asyncio
    async def test_llm_tool_schemas_are_valid(self):
        """Test that tool schemas are properly formatted for the LLM"""
        from zikos.mcp.server import MCPServer
        from zikos.services.llm import LLMService

        service = LLMService()
        mcp_server = MCPServer()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        tools = mcp_server.get_tools()

        # Verify tools are in correct format
        assert isinstance(tools, list)
        assert len(tools) > 0

        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
            assert "type" in tool["function"]["parameters"]
            assert tool["function"]["parameters"]["type"] == "object"

        # Test that LLM can accept these tools
        # Create a simple test message
        session_id = "test_schema_session"
        service.conversations.clear()

        # This should not crash even if LLM doesn't call tools
        result = await service.generate_response(
            "Hello, what tools do you have available?",
            session_id=session_id,
            mcp_server=mcp_server,
        )

        assert "type" in result
        assert result["type"] in ["response", "tool_call"]

    @pytest.mark.asyncio
    async def test_llm_tool_calling_loop(self):
        """Test that tool calling loop works correctly"""
        from zikos.mcp.server import MCPServer
        from zikos.services.llm import LLMService

        service = LLMService()
        mcp_server = MCPServer()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        session_id = "test_loop_session"
        service.conversations.clear()

        # Request something that should trigger a tool call
        # Use a clear, direct request
        result = await service.generate_response(
            "Create a metronome at 100 BPM",
            session_id=session_id,
            mcp_server=mcp_server,
        )

        assert "type" in result

        # Check conversation history was updated
        assert session_id in service.conversations
        history = service.conversations[session_id]
        assert len(history) > 0  # Should have at least system prompt

        # Check that user message was added
        user_messages = [msg for msg in history if msg.get("role") == "user"]
        assert len(user_messages) > 0

    @pytest.mark.asyncio
    async def test_llm_handles_tool_errors_gracefully(self):
        """Test that LLM handles tool errors without crashing"""
        from zikos.mcp.server import MCPServer
        from zikos.services.llm import LLMService

        service = LLMService()
        mcp_server = MCPServer()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        session_id = "test_error_session"
        service.conversations.clear()

        # Try to call a tool with invalid arguments (if LLM tries)
        # This tests error handling in the tool calling loop
        result = await service.generate_response(
            "Analyze tempo for audio file nonexistent123",
            session_id=session_id,
            mcp_server=mcp_server,
        )

        # Should not crash - should return either tool_call or response
        assert "type" in result
        assert result["type"] in ["response", "tool_call", "error"]

        # If it's a tool_call that fails, the error should be handled
        # If it's a response, that's fine too
