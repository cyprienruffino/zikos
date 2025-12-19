"""Main audio analysis tools class"""

from typing import Any

from zikos.mcp.tools.audio import (
    articulation,
    chords,
    comparison,
    dynamics,
    key,
    pitch,
    rhythm,
    tempo,
    timbre,
)
from zikos.mcp.tools.audio.utils import resolve_audio_path


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
            {
                "type": "function",
                "function": {
                    "name": "compare_audio",
                    "description": "Compare two audio recordings",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id_1": {"type": "string"},
                            "audio_file_id_2": {"type": "string"},
                            "comparison_type": {
                                "type": "string",
                                "enum": ["rhythm", "pitch", "tempo", "overall"],
                                "default": "overall",
                            },
                        },
                        "required": ["audio_file_id_1", "audio_file_id_2"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "compare_to_reference",
                    "description": "Compare audio to a reference (scale, exercise, MIDI file)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                            "reference_type": {
                                "type": "string",
                                "enum": ["scale", "exercise", "midi_file"],
                            },
                            "reference_params": {
                                "type": "object",
                                "description": "Parameters for reference (e.g., {'scale': 'C major', 'tempo': 120} or {'midi_file_id': 'midi_123'})",
                            },
                        },
                        "required": ["audio_file_id", "reference_type"],
                    },
                },
            },
        ]

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool"""
        if tool_name == "compare_audio":
            audio_file_id_1 = kwargs.get("audio_file_id_1")
            audio_file_id_2 = kwargs.get("audio_file_id_2")
            comparison_type = kwargs.get("comparison_type", "overall")

            if not audio_file_id_1 or not audio_file_id_2:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "audio_file_id_1 and audio_file_id_2 are required",
                }

            try:
                path_1 = str(resolve_audio_path(audio_file_id_1))
                path_2 = str(resolve_audio_path(audio_file_id_2))
            except FileNotFoundError as e:
                return {
                    "error": True,
                    "error_type": "FILE_NOT_FOUND",
                    "message": str(e),
                }

            result = await comparison.compare_audio(path_1, path_2, comparison_type)
            return dict(result)
        elif tool_name == "compare_to_reference":
            audio_file_id = kwargs.get("audio_file_id")
            reference_type = kwargs.get("reference_type")
            reference_params = kwargs.get("reference_params")

            if not audio_file_id or not reference_type:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "audio_file_id and reference_type are required",
                }

            try:
                resolved_path = str(resolve_audio_path(audio_file_id))
            except FileNotFoundError as e:
                return {
                    "error": True,
                    "error_type": "FILE_NOT_FOUND",
                    "message": str(e),
                }

            result = await comparison.compare_to_reference(
                resolved_path, reference_type, reference_params
            )
            return dict(result)

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
            result = await tempo.analyze_tempo(resolved_path)
            return dict(result)
        elif tool_name == "detect_pitch":
            result = await pitch.detect_pitch(resolved_path)
            return dict(result)
        elif tool_name == "analyze_rhythm":
            result = await rhythm.analyze_rhythm(resolved_path)
            return dict(result)
        elif tool_name == "analyze_dynamics":
            result = await dynamics.analyze_dynamics(resolved_path)
            return dict(result)
        elif tool_name == "analyze_articulation":
            result = await articulation.analyze_articulation(resolved_path)
            return dict(result)
        elif tool_name == "analyze_timbre":
            result = await timbre.analyze_timbre(resolved_path)
            return dict(result)
        elif tool_name == "detect_key":
            result = await key.detect_key(resolved_path)
            return dict(result)
        elif tool_name == "detect_chords":
            result = await chords.detect_chords(resolved_path)
            return dict(result)
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
