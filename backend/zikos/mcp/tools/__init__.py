"""MCP tools"""

from zikos.mcp.tools.analysis import AudioAnalysisTools
from zikos.mcp.tools.analysis.music_flamingo import MusicFlamingoTools
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

__all__ = [
    "AudioAnalysisTools",
    "MusicFlamingoTools",
    "MidiTools",
    "RecordingTools",
    "ChordProgressionTools",
    "EarTrainerTools",
    "MetronomeTools",
    "PracticeTimerTools",
    "TempoTrainerTools",
    "TunerTools",
]
