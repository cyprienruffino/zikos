"""Main audio analysis tools class"""

from pathlib import Path
from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio import (
    articulation,
    chords,
    comparison,
    comprehensive,
    dynamics,
    groove,
    instrument_detector,
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
from zikos.mcp.tools.audio.utils import is_valid_audio_file_id, resolve_audio_path
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

    @staticmethod
    def _invalid_id_error(tool_name: str, audio_file_id: Any) -> dict[str, Any]:
        return {
            "error": True,
            "error_type": "INVALID_PARAMETER",
            "message": (
                f"'{tool_name}' received audio_file_id '{audio_file_id}', which is not a UUID. "
                "audio_file_id must be a UUID returned by a prior tool call in the current "
                "session (e.g. from the audio upload notification, midi_to_audio, "
                "time_stretch, or pitch_shift). Do not fabricate or guess IDs."
            ),
        }

    async def call_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        """Call a tool (LLM-facing entry point).

        audio_file_id parameters are validated against the UUID format the
        system issues. Internal callers with a known file path should use the
        Python-level methods (e.g. analyze_tempo(audio_path=...)) instead;
        call_tool does not accept paths.
        """
        if tool_name == "compare_audio":
            audio_file_id_1 = kwargs.get("audio_file_id_1")
            audio_file_id_2 = kwargs.get("audio_file_id_2")
            comparison_type = kwargs.get("comparison_type", "overall")

            if not audio_file_id_1 or not audio_file_id_2:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": (
                        "compare_audio requires both audio_file_id_1 and audio_file_id_2 — "
                        "both must be valid audio UUIDs from the current session. "
                        "comparison_type must be one of: 'overall' (default), 'tempo', 'pitch', 'rhythm'."
                    ),
                }

            for file_id in (audio_file_id_1, audio_file_id_2):
                if not is_valid_audio_file_id(file_id):
                    return self._invalid_id_error(tool_name, file_id)

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
                    "message": (
                        "compare_to_reference requires audio_file_id (valid audio UUID) and reference_type. "
                        "Valid reference_type values: "
                        "'scale' (reference_params: {'scale': 'C major', 'tempo': 120}), "
                        "'midi_file' (reference_params: {'midi_file_id': '<id from validate_midi>'})."
                    ),
                }

            if not is_valid_audio_file_id(audio_file_id):
                return self._invalid_id_error(tool_name, audio_file_id)

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
                    "message": (
                        "segment_audio requires audio_file_id (valid audio UUID), "
                        "start_time (float, seconds from start, e.g. 0.0), and "
                        "end_time (float, seconds from start, must be greater than start_time). "
                        "Use get_audio_info first to check the total audio duration."
                    ),
                }

            if not is_valid_audio_file_id(audio_file_id):
                return self._invalid_id_error(tool_name, audio_file_id)

            result = await segmentation.segment_audio(audio_file_id, start_time, end_time)
            return dict(result)
        elif tool_name == "time_stretch":
            audio_file_id = kwargs.get("audio_file_id")
            rate = kwargs.get("rate")

            if not audio_file_id or rate is None:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": (
                        "time_stretch requires audio_file_id (valid audio UUID) and rate "
                        "(float, speed multiplier: 0.5=half speed, 1.0=unchanged, 2.0=double speed). "
                        "Returns a new audio_file_id for the stretched audio."
                    ),
                }

            if not is_valid_audio_file_id(audio_file_id):
                return self._invalid_id_error(tool_name, audio_file_id)

            result = await time_stretch_module.time_stretch(audio_file_id, rate)
            return dict(result)
        elif tool_name == "pitch_shift":
            audio_file_id = kwargs.get("audio_file_id")
            semitones = kwargs.get("semitones")

            if not audio_file_id or semitones is None:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": (
                        "pitch_shift requires audio_file_id (valid audio UUID) and semitones "
                        "(float, semitones to shift: positive=higher, negative=lower; "
                        "e.g. 2=up a whole step, -12=down an octave). "
                        "Returns a new audio_file_id for the shifted audio."
                    ),
                }

            if not is_valid_audio_file_id(audio_file_id):
                return self._invalid_id_error(tool_name, audio_file_id)

            result = await time_stretch_module.pitch_shift(audio_file_id, semitones)
            return dict(result)
        elif tool_name == "get_audio_info":
            audio_file_id = kwargs.get("audio_file_id")
            if not audio_file_id:
                return {
                    "error": True,
                    "error_type": "MISSING_PARAMETER",
                    "message": (
                        "get_audio_info requires audio_file_id — "
                        "provide a valid audio UUID from the current session."
                    ),
                }
            if not is_valid_audio_file_id(audio_file_id):
                return self._invalid_id_error(tool_name, audio_file_id)
            result = await self.get_audio_info(audio_file_id=audio_file_id)
            return dict(result)

        audio_file_id = kwargs.get("audio_file_id")

        if not audio_file_id:
            return {
                "error": True,
                "error_type": "MISSING_PARAMETER",
                "message": (
                    f"'{tool_name}' requires audio_file_id — "
                    "provide a valid audio UUID from the current session "
                    "(returned by the audio upload notification, midi_to_audio, time_stretch, or pitch_shift). "
                    "Do not fabricate or guess IDs."
                ),
            }
        if not is_valid_audio_file_id(audio_file_id):
            return self._invalid_id_error(tool_name, audio_file_id)

        try:
            resolved_path = str(resolve_audio_path(audio_file_id))
        except FileNotFoundError:
            return {
                "error": True,
                "error_type": "FILE_NOT_FOUND",
                "message": f"Audio file {audio_file_id} not found",
            }

        return await self._dispatch_analysis(tool_name, resolved_path)

    async def _dispatch_analysis(self, tool_name: str, resolved_path: str) -> dict[str, Any]:
        """Run a single-file analysis tool on an already-resolved path"""
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

    async def _run_internal(
        self, tool_name: str, audio_file_id: str | None, audio_path: str | None
    ) -> dict[str, Any]:
        """Internal (Python-level) entry point for services and tests.

        Unlike call_tool, this accepts an explicit audio_path so services that
        already know the file location (e.g. baseline analysis on upload) can
        run tools without minting an ID.
        """
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
                "message": f"'{tool_name}' requires audio_file_id or audio_path",
            }
        return await self._dispatch_analysis(tool_name, resolved_path)

    async def analyze_tempo(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("analyze_tempo", audio_file_id, audio_path)

    async def detect_pitch(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("detect_pitch", audio_file_id, audio_path)

    async def analyze_rhythm(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("analyze_rhythm", audio_file_id, audio_path)

    async def detect_instrument(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Detect instrument class from audio characteristics (always run as part of baseline)."""
        if audio_path:
            resolved_path = audio_path
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
                "message": "detect_instrument requires audio_file_id or audio_path",
            }
        return dict(await instrument_detector.detect_instrument(resolved_path))

    async def analyze_dynamics(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("analyze_dynamics", audio_file_id, audio_path)

    async def analyze_articulation(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("analyze_articulation", audio_file_id, audio_path)

    async def analyze_timbre(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("analyze_timbre", audio_file_id, audio_path)

    async def detect_key(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("detect_key", audio_file_id, audio_path)

    async def detect_chords(
        self, audio_file_id: str | None = None, audio_path: str | None = None
    ) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("detect_chords", audio_file_id, audio_path)

    async def segment_audio(
        self, audio_file_id: str, start_time: float, end_time: float
    ) -> dict[str, Any]:
        """Call a tool (internal entry point; the module resolves the ID itself)"""
        return dict(await segmentation.segment_audio(audio_file_id, start_time, end_time))

    async def segment_phrases(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("segment_phrases", audio_file_id, None)

    async def comprehensive_analysis(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("comprehensive_analysis", audio_file_id, None)

    async def analyze_groove(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("analyze_groove", audio_file_id, None)

    async def time_stretch(self, audio_file_id: str, rate: float) -> dict[str, Any]:
        """Call a tool (internal entry point; the module resolves the ID itself)"""
        return dict(await time_stretch_module.time_stretch(audio_file_id, rate))

    async def pitch_shift(self, audio_file_id: str, semitones: float) -> dict[str, Any]:
        """Call a tool (internal entry point; the module resolves the ID itself)"""
        return dict(await time_stretch_module.pitch_shift(audio_file_id, semitones))

    async def detect_repetitions(self, audio_file_id: str) -> dict[str, Any]:
        """Call a tool"""
        return await self._run_internal("detect_repetitions", audio_file_id, None)

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
                    "message": (
                        "get_audio_info requires audio_file_id — "
                        "provide a valid audio UUID from the current session."
                    ),
                }

            info = sf.info(resolved_path)
            return {
                "duration": info.duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format,
                "file_size_bytes": Path(resolved_path).stat().st_size,
            }
        except FileNotFoundError:
            ref = audio_file_id or audio_path or "unknown"
            return {
                "error": True,
                "error_type": "FILE_NOT_FOUND",
                "message": (
                    f"Audio file '{ref}' not found. "
                    "Provide a valid audio_file_id UUID from the current session."
                ),
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
