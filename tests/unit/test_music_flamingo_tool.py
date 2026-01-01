"""Unit tests for Music Flamingo MCP tool"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zikos.mcp.tools.analysis.music_flamingo import MusicFlamingoTools


@pytest.fixture
def music_flamingo_tools():
    """Create MusicFlamingoTools instance"""
    with patch("zikos.mcp.tools.analysis.music_flamingo.settings") as mock_settings:
        mock_settings.music_flamingo_service_url = "http://localhost:8001"
        tools = MusicFlamingoTools()
        return tools


class TestMusicFlamingoTools:
    """Tests for Music Flamingo tools"""

    def test_get_tools(self, music_flamingo_tools):
        """Test getting tool instances"""
        tools = music_flamingo_tools.get_tools()
        assert len(tools) == 1
        assert tools[0].name == "analyze_music_with_flamingo"
        assert tools[0].category.value == "audio_analysis"

    @pytest.mark.asyncio
    async def test_analyze_music_text_only(self, music_flamingo_tools):
        """Test text-only analysis"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "Analysis result"}
        mock_response.raise_for_status = MagicMock()

        music_flamingo_tools.client.post = AsyncMock(return_value=mock_response)

        result = await music_flamingo_tools.analyze_music_with_flamingo("Analyze this")

        assert "result" in result
        assert result["result"] == "Analysis result"
        music_flamingo_tools.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_music_with_audio(self, music_flamingo_tools):
        """Test analysis with audio file"""
        audio_path = Path("test_audio.wav")
        audio_path.write_bytes(b"fake audio")

        music_flamingo_tools.audio_service.get_audio_path = MagicMock(return_value=audio_path)

        upload_response = MagicMock()
        upload_response.json.return_value = {"audio_file_id": "flamingo_audio_id"}
        upload_response.raise_for_status = MagicMock()

        infer_response = MagicMock()
        infer_response.json.return_value = {"text": "Analysis with audio"}
        infer_response.raise_for_status = MagicMock()

        music_flamingo_tools.client.post = AsyncMock(side_effect=[upload_response, infer_response])

        result = await music_flamingo_tools.analyze_music_with_flamingo(
            "Analyze this", "test_audio_id"
        )

        assert "result" in result
        assert result["result"] == "Analysis with audio"
        assert music_flamingo_tools.client.post.call_count == 2

        audio_path.unlink()

    @pytest.mark.asyncio
    async def test_analyze_music_no_service_url(self):
        """Test error when service URL not configured"""
        with patch("zikos.mcp.tools.analysis.music_flamingo.settings") as mock_settings:
            mock_settings.music_flamingo_service_url = ""
            tools = MusicFlamingoTools()

            result = await tools.analyze_music_with_flamingo("Test")

            assert "error" in result
            assert "not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_analyze_music_audio_not_found(self, music_flamingo_tools):
        """Test error when audio file not found"""
        music_flamingo_tools.audio_service.get_audio_path = MagicMock(return_value=None)

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test", "nonexistent_id")

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_analyze_music_http_error(self, music_flamingo_tools):
        """Test handling of HTTP errors"""
        import httpx

        music_flamingo_tools.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Error",
                request=MagicMock(),
                response=MagicMock(status_code=500, text="Server error"),
            )
        )

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test")

        assert "error" in result
        assert "error" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self, music_flamingo_tools):
        """Test calling unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await music_flamingo_tools.call_tool("unknown_tool", text="test")

    @pytest.mark.asyncio
    async def test_analyze_music_audio_upload_http_error(self, music_flamingo_tools):
        """Test error handling when audio upload fails with HTTP error"""
        import httpx

        audio_path = Path("test_audio.wav")
        audio_path.write_bytes(b"fake audio")
        music_flamingo_tools.audio_service.get_audio_path = MagicMock(return_value=audio_path)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Upload failed"

        music_flamingo_tools.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Upload error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test", "test_audio_id")

        assert "error" in result
        assert "Failed to upload audio" in result["error"]
        assert "500" in result["error"]

        audio_path.unlink()

    @pytest.mark.asyncio
    async def test_analyze_music_audio_upload_general_error(self, music_flamingo_tools):
        """Test error handling when audio upload fails with general error"""
        audio_path = Path("test_audio.wav")
        audio_path.write_bytes(b"fake audio")
        music_flamingo_tools.audio_service.get_audio_path = MagicMock(return_value=audio_path)

        music_flamingo_tools.client.post = AsyncMock(side_effect=Exception("Network error"))

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test", "test_audio_id")

        assert "error" in result
        assert "Error uploading audio" in result["error"]

        audio_path.unlink()

    @pytest.mark.asyncio
    async def test_analyze_music_inference_http_error(self, music_flamingo_tools):
        """Test error handling when inference fails with HTTP error"""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        music_flamingo_tools.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Inference error",
                request=MagicMock(),
                response=mock_response,
            )
        )

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test")

        assert "error" in result
        assert "Music Flamingo service error" in result["error"]
        assert "503" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_music_inference_request_error(self, music_flamingo_tools):
        """Test error handling when inference fails with request error"""
        import httpx

        music_flamingo_tools.client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed", request=MagicMock())
        )

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test")

        assert "error" in result
        assert "Failed to connect to Music Flamingo service" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_music_inference_general_error(self, music_flamingo_tools):
        """Test error handling when inference fails with general error"""
        music_flamingo_tools.client.post = AsyncMock(side_effect=Exception("Unexpected error"))

        result = await music_flamingo_tools.analyze_music_with_flamingo("Test")

        assert "error" in result
        assert "Unexpected error" in result["error"]
