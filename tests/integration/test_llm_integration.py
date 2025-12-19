"""Integration tests for LLM service with real llama-cpp-python

These tests are marked as expensive and will be skipped by default.
Run them explicitly with: pytest -m "expensive" or pytest -m "llama"

These tests require:
- llama-cpp-python installed
- A valid LLM model file configured in settings
"""

import pytest

pytestmark = pytest.mark.expensive


class TestLLMServiceIntegration:
    """Integration tests for LLM service with real llama-cpp-python"""

    @pytest.mark.llama
    @pytest.mark.asyncio
    async def test_llm_initialization(self):
        """Test LLM initialization with real model"""
        from zikos.services.llm import LLMService

        service = LLMService()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        assert service.llm is not None

    @pytest.mark.llama
    @pytest.mark.asyncio
    async def test_llm_generate_response(self):
        """Test LLM response generation (expensive)"""
        from zikos.mcp.server import MCPServer
        from zikos.services.llm import LLMService

        service = LLMService()
        mcp_server = MCPServer()

        if service.llm is None:
            pytest.skip("LLM not initialized (no model file configured)")

        result = await service.generate_response(
            "Hello, this is a test message.",
            session_id="test_session",
            mcp_server=mcp_server,
        )

        assert "type" in result
        assert result["type"] in ["response", "tool_call"]
