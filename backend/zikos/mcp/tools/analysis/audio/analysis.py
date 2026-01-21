"""Main audio analysis tools class"""

from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.analysis.audio import (
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
from zikos.mcp.tools.analysis.audio import (
    time_stretch as time_stretch_module,
)
from zikos.mcp.tools.analysis.audio.utils import resolve_audio_path
from zikos.mcp.tools.base import ToolCollection


class AudioAnalysisTools(ToolCollection):
    """Audio analysis MCP tools"""

    def get_tools(self) -> list[Tool]:
        """Get Tool instances"""
        schemas = self._get_schema_dicts()
        return [
            Tool(
                name=schema["function"]["name"],
                description=schema["function"]["description"],
                category=ToolCategory.AUDIO_ANALYSIS,
                schema=schema,
            )
            for schema in schemas
        ]

    def _get_schema_dicts(self) -> list[dict[str, Any]]:
        """Get tool schemas as dicts (internal helper)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "analyze_tempo",
                    "description": """Analyze tempo/BPM and timing consistency.

Returns: dict with bpm, tempo_stability_score (0.0-1.0), is_steady, tempo_changes, rushing_detected, dragging_detected

Interpretation Guidelines:
- tempo_stability_score: >0.90 excellent, 0.80-0.90 good, <0.80 needs work
- When tempo_stability_score < 0.80 AND rushing_detected, consider suggesting metronome practice""",
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
                    "description": """Detect pitch and notes with intonation analysis.

Returns: dict with notes (with start_time, end_time, duration, pitch, frequency, confidence), intonation_accuracy (0.0-1.0), pitch_stability (0.0-1.0), detected_key, sharp_tendency, flat_tendency, average_cents_deviation

Interpretation Guidelines:
- intonation_accuracy: >0.90 excellent, 0.80-0.90 good, 0.70-0.80 needs work, <0.70 poor
- average_cents_deviation: <5 excellent, 5-15 good, 15-30 needs work, >30 poor
- pitch_stability: >0.90 excellent, 0.80-0.90 good, <0.80 needs work
- Reasoning patterns:
  * intonation_accuracy < 0.70 BUT pitch_stability > 0.85 → likely systematic issue (tuning, finger placement habit)
  * intonation_accuracy < 0.70 AND pitch_stability < 0.75 → likely technique issue (inconsistent pressure, hand position)
  * sharp_tendency > 0.15 → consistently sharp, check finger placement
  * flat_tendency > 0.15 → consistently flat, check finger placement""",
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
                    "description": """Analyze rhythm and timing accuracy.

Returns: dict with onsets, timing_accuracy (0.0-1.0), rhythmic_pattern, is_on_beat, beat_deviations, average_deviation_ms, rushing_tendency, dragging_tendency

Interpretation Guidelines:
- timing_accuracy: >0.90 excellent, 0.80-0.90 good, 0.70-0.80 needs work, <0.70 poor
- average_deviation_ms: <10ms excellent, 10-20ms good, 20-50ms needs work, >50ms poor
- rushing_tendency/dragging_tendency: <0.15 low, 0.15-0.30 moderate, >0.30 high
- When timing_accuracy < 0.80 AND rushing_tendency > 0.15, consider suggesting metronome practice
- When deviations are clustered, identify patterns (e.g., "rushing on the downbeat")""",
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
                    "description": """Analyze amplitude and dynamic range.

Returns: dict with dynamic_range (dB), dynamic_consistency (0.0-1.0), average_amplitude, peak_amplitude

Interpretation Guidelines:
- dynamic_range: >20dB excellent, 15-20dB good, 10-15dB needs work, <10dB poor
- dynamic_consistency: >0.85 excellent, 0.75-0.85 good, <0.75 needs work
- If dynamic_consistency < 0.75, suggest focusing on consistent technique""",
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
                    "description": """Analyze articulation types (staccato, legato, etc.).

Returns: dict with attack_time (ms), articulation_types, finger_noise (0.0-1.0), muting_effectiveness (0.0-1.0)

Interpretation Guidelines:
- attack_time: <10ms very fast (pick, slap), 10-20ms fast (clear attack), 20-50ms moderate (smooth), >50ms slow (legato)
- If attack_time varies significantly, focus on uniform attack
- finger_noise: <0.05 excellent, 0.05-0.10 good, 0.10-0.20 needs work, >0.20 poor
- muting_effectiveness: >0.90 excellent, 0.80-0.90 good, <0.80 needs work
- High finger_noise + low intonation_accuracy → likely related technique issues
- Low muting_effectiveness → suggest practicing muting technique""",
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
                    "description": """Analyze timbre and spectral characteristics to assess tone quality and identify instruments. Useful for evaluating tone production and technique.

Returns: dict with brightness (0.0-1.0), warmth (0.0-1.0), sharpness, spectral_centroid (Hz), spectral_rolloff, spectral_bandwidth, timbre_consistency, attack_time, harmonic_ratio (0.0-1.0)

Interpretation Guidelines:
- brightness: >0.7 high (violin, flute, trumpet), 0.4-0.7 medium (piano, guitar, saxophone), <0.4 low (cello, bass, trombone)
- warmth: >0.6 high (cello, bass, trombone), 0.4-0.6 medium (piano, guitar, saxophone), <0.4 low (violin, flute, piccolo)
- harmonic_ratio: >0.8 high (piano, strings, wind), 0.5-0.8 medium (guitar, some brass), <0.5 low (drums, percussion)
- spectral_centroid: >3000Hz bright, 1500-3000Hz balanced, <1500Hz warm
- Instrument identification patterns:
  * Piano: High harmonic_ratio (>0.85) + fast attack (<0.01) + medium brightness (0.5-0.7)
  * Guitar: Medium harmonic_ratio (0.6-0.8) + fast attack (<0.02) + medium warmth (0.4-0.6)
  * Violin: High brightness (>0.7) + high harmonic_ratio (>0.8) + fast attack (<0.02)
  * Bass: Low brightness (<0.4) + high warmth (>0.6) + low spectral centroid (<1500Hz)
- Combine brightness, warmth, harmonic_ratio, and attack_time to make identification. Provide confidence levels and explain which characteristics led to your conclusion.""",
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
                    "description": "Detect the musical key and mode (major/minor) of the audio. Useful for harmonic analysis and understanding the tonal center.",
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
                    "description": "Detect chord progression with chord names and timing. Identifies which chords are played and when they occur in the audio.",
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
                    "description": "Compare two audio recordings across tempo, pitch, rhythm, or overall performance. Useful for tracking progress between practice sessions or comparing different takes.",
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
            {
                "type": "function",
                "function": {
                    "name": "segment_audio",
                    "description": "Extract a segment from audio file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                            "start_time": {
                                "type": "number",
                                "description": "Start time in seconds",
                            },
                            "end_time": {"type": "number", "description": "End time in seconds"},
                        },
                        "required": ["audio_file_id", "start_time", "end_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "segment_phrases",
                    "description": "Detect musical phrase boundaries",
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
                    "name": "comprehensive_analysis",
                    "description": "Run all analyses and provide structured summary with strengths, weaknesses, and recommendations",
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
                    "name": "analyze_groove",
                    "description": "Analyze microtiming patterns, swing, and groove feel",
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
                    "name": "time_stretch",
                    "description": "Time-stretch audio without changing pitch (slow down or speed up)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                            "rate": {
                                "type": "number",
                                "description": "Stretch rate (0.25-4.0). 1.0 = no change, 0.5 = half speed, 2.0 = double speed",
                            },
                        },
                        "required": ["audio_file_id", "rate"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pitch_shift",
                    "description": "Pitch-shift audio without changing tempo (transpose)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {"type": "string"},
                            "semitones": {
                                "type": "number",
                                "description": "Number of semitones to shift (-24 to 24). Positive = higher, negative = lower",
                            },
                        },
                        "required": ["audio_file_id", "semitones"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_repetitions",
                    "description": "Detect repeated patterns and musical form",
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
                    "name": "get_audio_info",
                    "description": "Get basic audio file metadata (duration, sample rate, channels, format, file size)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "audio_file_id": {
                                "type": "string",
                                "description": "Audio file ID to get info for",
                            },
                        },
                        "required": ["audio_file_id"],
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

    async def segment_audio(
        self, audio_file_id: str, start_time: float, end_time: float
    ) -> dict[str, Any]:
        """Segment audio"""
        return await self.call_tool(
            "segment_audio",
            audio_file_id=audio_file_id,
            start_time=start_time,
            end_time=end_time,
        )

    async def segment_phrases(self, audio_file_id: str) -> dict[str, Any]:
        """Segment phrases"""
        return await self.call_tool("segment_phrases", audio_file_id=audio_file_id)

    async def comprehensive_analysis(self, audio_file_id: str) -> dict[str, Any]:
        """Comprehensive analysis"""
        return await self.call_tool("comprehensive_analysis", audio_file_id=audio_file_id)

    async def analyze_groove(self, audio_file_id: str) -> dict[str, Any]:
        """Analyze groove"""
        return await self.call_tool("analyze_groove", audio_file_id=audio_file_id)

    async def time_stretch(self, audio_file_id: str, rate: float) -> dict[str, Any]:
        """Time-stretch audio"""
        return await self.call_tool("time_stretch", audio_file_id=audio_file_id, rate=rate)

    async def pitch_shift(self, audio_file_id: str, semitones: float) -> dict[str, Any]:
        """Pitch-shift audio"""
        return await self.call_tool("pitch_shift", audio_file_id=audio_file_id, semitones=semitones)

    async def detect_repetitions(self, audio_file_id: str) -> dict[str, Any]:
        """Detect repetitions"""
        return await self.call_tool("detect_repetitions", audio_file_id=audio_file_id)

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
