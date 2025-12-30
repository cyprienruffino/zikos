"""Music Flamingo analysis tools"""

from pathlib import Path
from typing import Any

import httpx

from zikos.config import settings
from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.base import ToolCollection


class MusicFlamingoTools(ToolCollection):
    """Music Flamingo analysis MCP tools"""

    def __init__(self):
        self.service_url = settings.music_flamingo_service_url
        self.client = httpx.AsyncClient(timeout=300.0)
        self._audio_service = None

    @property
    def audio_service(self):
        """Lazy load AudioService to avoid circular imports"""
        if self._audio_service is None:
            from zikos.services.audio import AudioService

            self._audio_service = AudioService()
        return self._audio_service

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        return [
            Tool(
                name="analyze_music_with_flamingo",
                description=(
                    "Analyze music using Music Flamingo, a state-of-the-art multimodal AI model "
                    "that can understand both audio and text. Use this for deep musical analysis, "
                    "understanding performance nuances, comparing performances, or getting "
                    "semantic insights about music that go beyond signal processing. "
                    "This tool provides rich, context-aware analysis of musical performances."
                ),
                category=ToolCategory.AUDIO_ANALYSIS,
                schema={
                    "type": "function",
                    "function": {
                        "name": "analyze_music_with_flamingo",
                        "description": (
                            "Analyze music using Music Flamingo, a state-of-the-art multimodal AI model "
                            "that can understand both audio and text. Use this for deep musical analysis, "
                            "understanding performance nuances, comparing performances, or getting "
                            "semantic insights about music that go beyond signal processing."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": (
                                        "The analysis prompt or question. Be specific about what you want to analyze. "
                                        "Examples: 'Analyze this performance and identify the main technical issues', "
                                        "'Compare this performance to the reference and highlight differences', "
                                        "'Describe the musical expression and emotional content of this performance'"
                                    ),
                                },
                                "audio_file_id": {
                                    "type": "string",
                                    "description": (
                                        "Optional audio file ID from the main service's audio storage. "
                                        "The audio will be uploaded to Music Flamingo service for analysis. "
                                        "If not provided, the analysis will be text-only."
                                    ),
                                },
                            },
                            "required": ["text"],
                        },
                    },
                },
            ),
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "analyze_music_with_flamingo":
            return await self.analyze_music_with_flamingo(
                kwargs["text"],
                kwargs.get("audio_file_id"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def analyze_music_with_flamingo(
        self, text: str, audio_file_id: str | None = None
    ) -> dict[str, Any]:
        """Analyze music using Music Flamingo service"""
        if not self.service_url:
            return {
                "error": "Music Flamingo service URL not configured. Set MUSIC_FLAMINGO_SERVICE_URL environment variable.",
            }

        music_flamingo_audio_id = None

        if audio_file_id:
            try:
                audio_path = self.audio_service.get_audio_path(audio_file_id)
                if not audio_path or not audio_path.exists():
                    return {"error": f"Audio file not found: {audio_file_id}"}

                audio_content = audio_path.read_bytes()
                files = {"file": (audio_path.name, audio_content, "audio/wav")}
                upload_response = await self.client.post(
                    f"{self.service_url}/api/v1/upload", files=files
                )
                upload_response.raise_for_status()
                upload_result = upload_response.json()
                music_flamingo_audio_id = upload_result["audio_file_id"]
            except httpx.HTTPStatusError as e:
                return {
                    "error": f"Failed to upload audio to Music Flamingo service: {e.response.status_code} - {e.response.text}",
                }
            except Exception as e:
                return {"error": f"Error uploading audio: {str(e)}"}

        try:
            response = await self.client.post(
                f"{self.service_url}/api/v1/infer",
                json={"text": text, "audio_file_id": music_flamingo_audio_id},
            )
            response.raise_for_status()
            result = response.json()
            return {"result": result["text"]}
        except httpx.HTTPStatusError as e:
            return {
                "error": f"Music Flamingo service error: {e.response.status_code} - {e.response.text}",
            }
        except httpx.RequestError as e:
            return {
                "error": f"Failed to connect to Music Flamingo service: {str(e)}",
            }
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
