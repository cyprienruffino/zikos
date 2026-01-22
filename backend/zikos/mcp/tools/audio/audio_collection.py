"""Main audio analysis tools class"""

from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio import (
    articulation,
    chords,
    comparison,
    comprehensive,
    dynamics,
    groove,
    key,
    phrase_segmentation,
    pitch,
    repetition,
    rhythm,
    segmentation,
    tempo,
    timbre,
)
from zikos.mcp.tools.audio import (
    time_stretch as time_stretch_module,
)
from zikos.mcp.tools.audio.utils import resolve_audio_path
from zikos.mcp.tools.base import ToolCollection


class AudioAnalysisTools(ToolCollection):
    """Audio analysis MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances - collects from individual modules"""
        tools = []

        # Collect tools from individual modules
        tools.append(tempo.get_analyze_tempo_tool())
        tools.append(pitch.get_detect_pitch_tool())
        tools.append(rhythm.get_analyze_rhythm_tool())
        tools.append(dynamics.get_analyze_dynamics_tool())
        tools.append(articulation.get_analyze_articulation_tool())
        tools.append(timbre.get_analyze_timbre_tool())
        tools.append(key.get_detect_key_tool())
        tools.append(chords.get_detect_chords_tool())
        tools.append(comparison.get_compare_audio_tool())
        tools.append(comparison.get_compare_to_reference_tool())
        tools.append(segmentation.get_segment_audio_tool())
        tools.append(phrase_segmentation.get_segment_phrases_tool())
        tools.append(comprehensive.get_comprehensive_analysis_tool())
        tools.append(groove.get_analyze_groove_tool())
        tools.append(time_stretch_module.get_time_stretch_tool())
        tools.append(time_stretch_module.get_pitch_shift_tool())
        tools.append(repetition.get_detect_repetitions_tool())

        # get_audio_info is defined in this collection
        tools.append(
            Tool(
                name="get_audio_info",
                description="Get basic audio file metadata (duration, sample rate, channels, format, file size)",
                category=ToolCategory.AUDIO_ANALYSIS,
                parameters={
                    "audio_file_id": {
                        "type": "string",
                        "description": "Audio file ID to get info for",
                    },
                },
                required=["audio_file_id"],
                detailed_description="""Get basic audio file metadata.

Returns: dict with duration (seconds), sample_rate (Hz), channels (1=mono, 2=stereo), format (file format), file_size_bytes

Interpretation Guidelines:
- duration: Length of audio in seconds - use to check if recording is complete
- sample_rate: Audio quality indicator - 44100Hz or 48000Hz is standard, lower may indicate quality issues
- channels: 1 = mono, 2 = stereo - stereo provides better spatial information
- format: File format (WAV, MP3, etc.) - WAV is uncompressed, best for analysis
- file_size_bytes: File size - very small files may be corrupted or empty
- Use to verify audio file before analysis or to provide context about recording quality
- Low sample_rate (<22050Hz) may affect pitch detection accuracy
- Very short duration (<0.5s) may not be suitable for most analyses""",
            )
        )

        return tools

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
        elif tool_name == "segment_audio":
            audio_file_id = kwargs.get("audio_file_id")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")

            if not audio_file_id or start_time is None or end_time is None:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "audio_file_id, start_time, and end_time are required",
                }

            result = await segmentation.segment_audio(audio_file_id, start_time, end_time)
            return dict(result)
        elif tool_name == "time_stretch":
            audio_file_id = kwargs.get("audio_file_id")
            rate = kwargs.get("rate")

            if not audio_file_id or rate is None:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "audio_file_id and rate are required",
                }

            result = await time_stretch_module.time_stretch(audio_file_id, rate)
            return dict(result)
        elif tool_name == "pitch_shift":
            audio_file_id = kwargs.get("audio_file_id")
            semitones = kwargs.get("semitones")

            if not audio_file_id or semitones is None:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": "audio_file_id and semitones are required",
                }

            result = await time_stretch_module.pitch_shift(audio_file_id, semitones)
            return dict(result)
        elif tool_name == "get_audio_info":
            audio_file_id = kwargs.get("audio_file_id")
            audio_path = kwargs.get("audio_path")
            result = await self.get_audio_info(audio_file_id=audio_file_id, audio_path=audio_path)
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
        elif tool_name == "segment_phrases":
            result = await phrase_segmentation.segment_phrases(resolved_path)
            return dict(result)
        elif tool_name == "comprehensive_analysis":
            result = await comprehensive.comprehensive_analysis(resolved_path)
            return dict(result)
        elif tool_name == "analyze_groove":
            result = await groove.analyze_groove(resolved_path)
            return dict(result)
        elif tool_name == "detect_repetitions":
            result = await repetition.detect_repetitions(resolved_path)
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
        """Call a tool"""
        return await self.call_tool(
            "analyze_tempo", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def detect_pitch(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "detect_pitch", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_rhythm(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "analyze_rhythm", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_dynamics(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "analyze_dynamics", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_articulation(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "analyze_articulation", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def analyze_timbre(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "analyze_timbre", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def detect_key(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "detect_key", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def detect_chords(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "detect_chords", audio_file_id=audio_file_id, audio_path=audio_path
        )

    async def segment_audio(
        self, audio_file_id: str, start_time: float, end_time: float
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool(
            "segment_audio",
            audio_file_id=audio_file_id,
            start_time=start_time,
            end_time=end_time,
        )

    async def segment_phrases(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool("segment_phrases", audio_file_id=audio_file_id)

    async def comprehensive_analysis(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool("comprehensive_analysis", audio_file_id=audio_file_id)

    async def analyze_groove(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool("analyze_groove", audio_file_id=audio_file_id)

    async def time_stretch(self, audio_file_id: str, rate: float) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool("time_stretch", audio_file_id=audio_file_id, rate=rate)

    async def pitch_shift(self, audio_file_id: str, semitones: float) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool("pitch_shift", audio_file_id=audio_file_id, semitones=semitones)

    async def detect_repetitions(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self.call_tool("detect_repetitions", audio_file_id=audio_file_id)

    async def get_audio_info(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
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
