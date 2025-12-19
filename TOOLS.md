# MCP Tools Specification

## Tool Output Design Principles

All tools must return **LLM-interpretable** structured data. This means:

1. **Musical Context**: Metrics have clear musical meaning
2. **Normalized Scores**: Use 0.0-1.0 scores where applicable (higher = better)
3. **Musical Terminology**: Use note names, chord names, keys (not just frequencies)
4. **Time References**: Include precise time locations for all events/issues
5. **Severity Indicators**: Include severity levels for problems
6. **Reference Ranges**: Document what "good" looks like (see SYSTEM_PROMPT.md)

See [AUDIO_ANALYSIS_TOOLS.md](./AUDIO_ANALYSIS_TOOLS.md) for detailed LLM-interpretability requirements.

## Tool Categories

### Baseline Tools (Always Run)
These tools are automatically called for every audio submission to provide fundamental analysis.

#### `analyze_tempo(audio_file_id: str) -> dict`
**Purpose**: Detect tempo/BPM and timing consistency

**Returns**:
```json
{
  "bpm": 120.5,
  "confidence": 0.9,
  "is_steady": true,
  "tempo_stability_score": 0.91,
  "tempo_changes": [
    {"time": 0.0, "bpm": 120.0, "confidence": 0.9},
    {"time": 15.3, "bpm": 121.2, "confidence": 0.9}
  ],
  "rushing_detected": false,
  "dragging_detected": false
}
```

#### `detect_pitch(audio_file_id: str) -> dict`
**Purpose**: Note-by-note pitch detection and intonation analysis

**Returns**:
```json
{
  "notes": [
    {
      "start_time": 0.0,
      "end_time": 0.5,
      "duration": 0.5,
      "pitch": "C4",
      "frequency": 261.63,
      "confidence": 0.95
    },
    {
      "start_time": 0.5,
      "end_time": 1.0,
      "duration": 0.5,
      "pitch": "D4",
      "frequency": 293.66,
      "confidence": 0.92
    }
  ],
  "intonation_accuracy": 0.88,
  "pitch_stability": 0.91,
  "detected_key": "C major",
  "sharp_tendency": 0.12,
  "flat_tendency": 0.08
}
```

#### `analyze_rhythm(audio_file_id: str) -> dict`
**Purpose**: Onset detection, timing accuracy, rhythmic patterns

**Returns**:
```json
{
  "onsets": [
    {"time": 0.0, "confidence": 0.94},
    {"time": 0.5, "confidence": 0.91}
  ],
  "timing_accuracy": 0.87,
  "rhythmic_pattern": "regular",
  "is_on_beat": true,
  "beat_deviations": [
    {"time": 2.3, "deviation_ms": -15, "severity": "minor"}
  ],
  "average_deviation_ms": -8.5,
  "rushing_tendency": 0.12,
  "dragging_tendency": 0.08
}
```

### Optional Analysis Tools (LLM Decides)

#### `detect_key(audio_file_id: str) -> dict`
**Purpose**: Musical key detection

**Returns**:
```json
{
  "key": "C major",
  "confidence": 0.89,
  "mode": "major",
  "tonic": "C"
}
```

#### `detect_chords(audio_file_id: str) -> dict`
**Purpose**: Chord progression analysis

**Returns**:
```json
{
  "chords": [
    {"time": 0.0, "duration": 2.0, "chord": "Cmaj", "confidence": 0.93},
    {"time": 2.0, "duration": 2.0, "chord": "Amin", "confidence": 0.91}
  ],
  "progression": ["Cmaj", "Amin", "Fmaj", "Gmaj"]
}
```

#### `analyze_timbre(audio_file_id: str) -> dict`
**Purpose**: Spectral characteristics, tone quality

**Returns**:
```json
{
  "brightness": 0.72,
  "warmth": 0.65,
  "sharpness": 0.58,
  "spectral_centroid": 2500.0,
  "spectral_rolloff": 5000.0,
  "spectral_bandwidth": 1500.0,
  "timbre_consistency": 0.84,
  "attack_time": 0.015,
  "harmonic_ratio": 0.85
}
```

#### `segment_phrases(audio_file_id: str) -> dict`
**Purpose**: Detect musical phrase boundaries

**Returns**:
```json
{
  "phrases": [
    {"start": 0.0, "end": 4.0, "type": "melodic", "confidence": 0.92},
    {"start": 4.0, "end": 8.0, "type": "melodic", "confidence": 0.89}
  ],
  "phrase_count": 2,
  "average_phrase_length": 4.0
}
```

#### `comprehensive_analysis(audio_file_id: str) -> dict`
**Purpose**: Run all analyses and provide structured summary with strengths, weaknesses, and recommendations

**Returns**:
```json
{
  "timing": {
    "tempo": {...},
    "rhythm": {...}
  },
  "pitch": {...},
  "dynamics": {...},
  "frequency": {
    "timbre": {...}
  },
  "musical_structure": {
    "key": {...},
    "chords": {...},
    "phrases": {...}
  },
  "articulation": {...},
  "overall_score": 0.87,
  "strengths": ["timing", "intonation"],
  "weaknesses": ["dynamic_consistency"],
  "recommendations": ["Practice with metronome to improve tempo consistency"]
}
```

**Note**: This tool runs all available analysis tools in parallel and provides a comprehensive summary. It's useful when you need a complete overview of the performance.

#### `analyze_groove(audio_file_id: str) -> dict`
**Purpose**: Analyze microtiming patterns, swing, and groove feel

**Returns**:
```json
{
  "groove_type": "straight",
  "swing_ratio": 1.0,
  "microtiming_pattern": "consistent",
  "feel_score": 0.89,
  "groove_consistency": 0.92,
  "average_microtiming_deviation_ms": 8.5,
  "microtiming_std_ms": 12.3
}
```

**Note**: `groove_type` can be "straight", "swung", or "reverse_swing". `swing_ratio` of 1.0 means straight time, >1.3 indicates swing.

#### `detect_repetitions(audio_file_id: str) -> dict`
**Purpose**: Detect repeated patterns and identify musical form

**Returns**:
```json
{
  "repetitions": [
    {
      "pattern_start": 0.0,
      "pattern_end": 4.0,
      "repetition_times": [4.0, 8.0],
      "similarity": 0.92
    }
  ],
  "form": "A-A-B-A"
}
```

**Note**: Identifies repeated patterns using chroma-based similarity analysis. Form labels (A, B, C, etc.) represent different patterns.

#### `analyze_dynamics(audio_file_id: str) -> dict`
**Purpose**: Volume/amplitude analysis

**Returns**:
```json
{
  "average_rms": -12.5,
  "average_loudness": -12.5,
  "peak_amplitude": -8.1,
  "dynamic_range_db": 15.3,
  "dynamic_range": 15.3,
  "lufs": -14.2,
  "amplitude_envelope": [
    {"time": 0.0, "rms": -12.5},
    {"time": 0.1, "rms": -12.3}
  ],
  "dynamic_consistency": 0.87,
  "is_consistent": true,
  "peaks": [
    {"time": 3.2, "amplitude": -8.1}
  ]
}
```

**Note**: Both `average_rms`/`average_loudness` and `dynamic_range_db`/`dynamic_range` are provided for compatibility. `is_consistent` is derived from `dynamic_consistency` (threshold: 0.75).

#### `analyze_articulation(audio_file_id: str) -> dict`
**Purpose**: Staccato, legato, accents analysis

**Returns**:
```json
{
  "articulation_types": ["legato", "staccato"],
  "legato_percentage": 0.65,
  "staccato_percentage": 0.35,
  "articulation_consistency": 0.82,
  "accents": [
    {
      "time": 1.5,
      "intensity": 0.82,
      "relative_loudness": 1.25
    }
  ]
}
```

### Comparison Tools

#### `compare_audio(audio_file_id_1: str, audio_file_id_2: str, comparison_type: str) -> dict`
**Purpose**: Compare two audio recordings

**Parameters**:
- `audio_file_id_1`: First audio file ID
- `audio_file_id_2`: Second audio file ID
- `comparison_type`: "rhythm" | "pitch" | "tempo" | "overall" (default: "overall")

**Returns**:
```json
{
  "comparison_type": "overall",
  "similarity_score": 0.78,
  "differences": {
    "tempo": {
      "audio1": 120.0,
      "audio2": 118.5,
      "difference": 1.5,
      "stability_audio1": 0.91,
      "stability_audio2": 0.93
    },
    "pitch_accuracy": {
      "audio1": 0.88,
      "audio2": 0.92,
      "improvement": 0.04
    },
    "pitch_stability": {
      "audio1": 0.85,
      "audio2": 0.87,
      "improvement": 0.02
    },
    "rhythm_accuracy": {
      "audio1": 0.85,
      "audio2": 0.87,
      "improvement": 0.02
    },
    "timing_deviation": {
      "audio1": -8.5,
      "audio2": -6.2,
      "improvement": 2.3
    }
  },
  "improvements": ["pitch_accuracy", "rhythm_accuracy"],
  "regressions": []
}
```

**Note**: `similarity_score` is only calculated when `comparison_type` is "overall".

#### `compare_to_reference(audio_file_id: str, reference_type: str, reference_params: dict) -> dict`
**Purpose**: Compare student performance to a reference (scale, exercise, MIDI file)

**Parameters**:
- `audio_file_id`: Audio file ID to compare
- `reference_type`: "scale" | "midi_file" (note: "exercise" not yet implemented)
- `reference_params`: Parameters for reference:
  - For "scale": `{"scale": "C major", "tempo": 120}` (tempo optional)
  - For "midi_file": `{"midi_file_id": "midi_123"}`

**Returns** (for scale):
```json
{
  "reference_type": "scale",
  "scale": "C major",
  "comparison": {
    "pitch_accuracy": 0.89,
    "rhythm_accuracy": 0.82,
    "tempo_match": 0.91
  },
  "errors": [
    {
      "time": 2.3,
      "type": "wrong_note",
      "expected": "note in C major",
      "played": "F4"
    }
  ],
  "detected_key": "C major"
}
```

**Returns** (for MIDI file):
```json
{
  "reference_type": "midi_file",
  "midi_file_id": "midi_123",
  "comparison": {
    "pitch_accuracy": 0.89,
    "rhythm_accuracy": 0.82,
    "tempo_match": 0.91
  },
  "errors": []
}
```

### Audio Recording Tools

#### `request_audio_recording(prompt: str, max_duration: float) -> dict`
**Purpose**: Request user to record audio sample

**Parameters**:
- `prompt`: Instructions for what to record (e.g., "Please play the C major scale")
- `max_duration`: Maximum recording duration in seconds (optional, default: 60.0)

**Returns**:
```json
{
  "status": "recording_requested",
  "prompt": "Please play the C major scale",
  "max_duration": 60.0,
  "recording_id": "rec_abc123"
}
```

**UI Behavior**: When this tool is called, UI should show recording interface with the prompt displayed.

**After Recording**:
```json
{
  "status": "completed",
  "audio_file_id": "audio_xyz789",
  "recording_id": "rec_abc123",
  "duration": 8.5
}
```

### MIDI Processing Tools

#### `validate_midi(midi_text: str) -> dict`
**Purpose**: Validate MIDI syntax generated by LLM

**Parameters**:
- `midi_text`: MIDI text generated by LLM (in standard MIDI format or simplified format)

**Returns**:
```json
{
  "valid": true,
  "midi_file_id": "midi_abc123",
  "errors": [],
  "warnings": [],
  "metadata": {
    "duration": 8.0,
    "tempo": 120,
    "tracks": 1,
    "note_count": 8
  }
}
```

**Error Example**:
```json
{
  "valid": false,
  "errors": [
    "Invalid note format at line 5: 'C5' should be 'C5 60'",
    "Missing tempo marker"
  ],
  "warnings": [
    "No time signature specified, defaulting to 4/4"
  ]
}
```

**Note**: LLM generates MIDI directly in its response. This tool validates and parses it.

#### `midi_to_audio(midi_file_id: str, instrument: str) -> dict`
**Purpose**: Synthesize MIDI to audio

**Parameters**:
- `instrument`: "piano" | "guitar" | "violin" | "bass" | etc. (maps to FluidSynth soundfont)

**Returns**:
```json
{
  "audio_file_id": "audio_xyz789",
  "midi_file_id": "midi_abc123",
  "instrument": "piano",
  "duration": 8.0,
  "synthesis_method": "fluidsynth"
}
```

**Note**: For POC, uses FluidSynth. Future: neural synthesis for better timbre/technique demonstration.

#### `midi_to_notation(midi_file_id: str, format: str) -> dict`
**Purpose**: Render MIDI to sheet music/tabs

**Parameters**:
- `format`: "sheet_music" | "tabs" | "both"

**Returns**:
```json
{
  "midi_file_id": "midi_abc123",
  "sheet_music_url": "/notation/sheet_abc123.png",
  "tabs_url": "/notation/tabs_abc123.png",
  "format": "both"
}
```

### Utility Tools

#### `get_audio_info(audio_file_id: str) -> dict`
**Purpose**: Get basic audio file metadata

**Status**: ⚠️ **Not exposed as MCP tool** - Implemented internally but not available to LLM

**Returns** (when exposed):
```json
{
  "duration": 10.5,
  "sample_rate": 44100,
  "channels": 1,
  "format": "wav",
  "file_size_bytes": 925440
}
```

#### `segment_audio(audio_file_id: str, start_time: float, end_time: float) -> dict`
**Purpose**: Extract segment from audio

**Parameters**:
- `audio_file_id`: Audio file ID to segment
- `start_time`: Start time in seconds (must be >= 0)
- `end_time`: End time in seconds (must be > start_time)

**Returns**:
```json
{
  "new_audio_file_id": "audio_segmented_xyz",
  "original_audio_file_id": "audio_abc123",
  "start_time": 2.0,
  "end_time": 5.0,
  "duration": 3.0
}
```

#### `time_stretch(audio_file_id: str, rate: float) -> dict`
**Purpose**: Time-stretch audio without changing pitch (slow down or speed up)

**Parameters**:
- `audio_file_id`: Audio file ID to stretch
- `rate`: Stretch rate (0.25-4.0). 1.0 = no change, 0.5 = half speed, 2.0 = double speed

**Returns**:
```json
{
  "new_audio_file_id": "audio_stretched_xyz",
  "original_audio_file_id": "audio_abc123",
  "rate": 0.5,
  "original_duration": 4.0,
  "new_duration": 8.0
}
```

**Note**: Requires `pyrubberband` library. Useful for practice (slow down difficult passages) or demonstration (speed up).

#### `pitch_shift(audio_file_id: str, semitones: float) -> dict`
**Purpose**: Pitch-shift audio without changing tempo (transpose)

**Parameters**:
- `audio_file_id`: Audio file ID to shift
- `semitones`: Number of semitones to shift (-24 to 24). Positive = higher, negative = lower

**Returns**:
```json
{
  "new_audio_file_id": "audio_shifted_xyz",
  "original_audio_file_id": "audio_abc123",
  "semitones": 2.0,
  "duration": 4.0
}
```

**Note**: Requires `pyrubberband` library. Useful for transposition or demonstrating different keys.

## Tool Implementation Notes

### Error Handling
All tools should return structured errors:
```json
{
  "error": true,
  "error_type": "INVALID_AUDIO" | "TOO_SHORT" | "PROCESSING_FAILED",
  "message": "Audio file is too short (minimum 0.5 seconds required)",
  "details": {}
}
```

### Performance Considerations
- Tools should cache results when possible
- Long-running tools should support async processing
- Tools should validate input audio format and duration

### Tool Discovery
Tools should provide metadata for LLM discovery:
- Name and description
- Required parameters
- Return type schema
- Example usage
