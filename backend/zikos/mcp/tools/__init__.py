"""MCP tools"""

from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.interaction import (
    ChordProgressionTools,
    EarTrainerTools,
    MetronomeTools,
    PracticeTimerTools,
    RecordingTools,
    TempoTrainerTools,
    TunerTools,
)
from zikos.mcp.tools.processing import MidiTools
from zikos.mcp.tools.system import SystemTools

__all__ = [
    "AudioAnalysisTools",
    "MidiTools",
    "RecordingTools",
    "ChordProgressionTools",
    "EarTrainerTools",
    "MetronomeTools",
    "PracticeTimerTools",
    "TempoTrainerTools",
    "TunerTools",
    "SystemTools",
]
