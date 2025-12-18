"""Main audio analysis tools class"""

from typing import Any

from src.zikos.mcp.tools.audio import (
    articulation,
    chords,
    dynamics,
    key,
    pitch,
    rhythm,
    tempo,
    timbre,
)
from src.zikos.mcp.tools.audio.utils import resolve_audio_path


class AudioAnalysisTools:
    """Audio analysis MCP tools"""

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "analyze_tempo",
                    "description": "Analyze tempo/BPM and timing consistency",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_pitch",
                    "description": "Detect pitch and notes with intonation analysis",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_rhythm",
                    "description": "Analyze rhythm and timing accuracy",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_dynamics",
                    "description": "Analyze amplitude and dynamic range",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_articulation",
                    "description": "Analyze articulation types (staccato, legato, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_timbre",
                    "description": "Analyze timbre and spectral characteristics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_key",
                    "description": "Detect musical key",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_chords",
                    "description": "Detect chord progression",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                        },
                        "required": ["audio_file_id"],
                    },
                },
            },
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        audio_file_id = kwargs.get("audio_file_id")
        audio_path = kwargs.get("audio_path")

        if audio_path:
            resolved_path = str(audio_path)
        elif audio_file_id:
            try:
                resolved_path = str(resolve_audio_path(audio_file_id))
            except FileNotFoundError:
                return {
                    "error": True,
                    "error_type": "FILE_NOT_FOUND",
                    "message": f"Audio file {audio_file_id} not found",
                }
        else:
            return {
                "error": True,
                "error_type": "MISSING_PARAMETER",
                "message": "audio_file_id or audio_path is required",
            }

        if tool_name == "analyze_tempo":
            return await tempo.analyze_tempo(resolved_path)
        elif tool_name == "detect_pitch":
            return await pitch.detect_pitch(resolved_path)
        elif tool_name == "analyze_rhythm":
            return await rhythm.analyze_rhythm(resolved_path)
        elif tool_name == "analyze_dynamics":
            return await dynamics.analyze_dynamics(resolved_path)
        elif tool_name == "analyze_articulation":
            return await articulation.analyze_articulation(resolved_path)
        elif tool_name == "analyze_timbre":
            return await timbre.analyze_timbre(resolved_path)
        elif tool_name == "detect_key":
            return await key.detect_key(resolved_path)
        elif tool_name == "detect_chords":
            return await chords.detect_chords(resolved_path)
        else:
            return {
                "error": True,
                "error_type": "UNKNOWN_TOOL",
                "message": f"Unknown tool: {tool_name}",
            }

    async def analyze_tempo(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Analyze tempo"""
        return await self.call_tool(
            "analyze_tempo", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def detect_pitch(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Detect pitch"""
        return await self.call_tool(
            "detect_pitch", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_rhythm(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Analyze rhythm"""
        return await self.call_tool(
            "analyze_rhythm", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_dynamics(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Analyze dynamics"""
        return await self.call_tool(
            "analyze_dynamics", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_articulation(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Analyze articulation"""
        return await self.call_tool(
            "analyze_articulation", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_timbre(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Analyze timbre"""
        return await self.call_tool(
            "analyze_timbre", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def detect_key(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Detect key"""
        return await self.call_tool(
            "detect_key", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def detect_chords(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Detect chords"""
        return await self.call_tool(
            "detect_chords", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def get_audio_info(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Get audio info"""
        import soundfile as sf

        try:
            if audio_path:
                resolved_path = audio_path
            elif audio_file_id:
                resolved_path = str(resolve_audio_path(audio_file_id))
            else:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "audio_file_id or audio_path is required",
                }

            info = sf.info(resolved_path)
            return {
                "duration": info.duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format,
                "file_size_bytes": info.frames * info.channels * info.samplerate,
            }
        except FileNotFoundError:
            return {
                "error": True,
                "error_type": "FILE_NOT_FOUND",
                "message": "Audio file not found",
            }
        except Exception as e:
            error_str = str(e).lower()
            if (
                "error opening" in error_str
                or "not found" in error_str
                or "no such file" in error_str
            ):
                return {
                    "error": True,
                    "error_type": "FILE_NOT_FOUND",
                    "message": "Audio file not found",
                }
            return {
                "error": True,
                "error_type": "PROCESSING_FAILED",
                "message": f"Failed to get audio info: {str(e)}",
            }
