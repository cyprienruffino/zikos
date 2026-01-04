# MCP Tools Reference

## Design Principles

### Tool Output Design
All tools must return **LLM-interpretable** structured data:

1. **Musical Context**: Metrics have clear musical meaning
   - ✅ Good: `"timing_accuracy": 0.87` with interpretation guidelines
   - ❌ Bad: Raw FFT coefficients or uninterpreted signal processing values

2. **Normalized Scores**: Use 0.0-1.0 scores where applicable (higher = better)
   - Provide reference ranges: Excellent (>0.90), Good (0.80-0.90), Needs Work (0.70-0.80), Poor (<0.70)

3. **Musical Terminology**: Use note names, chord names, keys (not just frequencies)
   - ✅ Good: `"pitch": "C4", "chord": "Cmaj", "key": "C major"`
   - ❌ Bad: `"frequency": 261.63` without note name

4. **Time References**: Include precise time locations for all events/issues
   - ✅ Good: `{"time": 2.3, "issue": "wrong_note", "expected": "E4", "played": "F4"}`
   - ❌ Bad: `{"issue": "wrong_note"}` without location

5. **Severity Indicators**: Include severity levels for problems
   - ✅ Good: `{"deviation_ms": -15, "severity": "minor"}`
   - ❌ Bad: `{"deviation_ms": -15}` without context

6. **Descriptive Fields**: Include both quantitative metrics and qualitative descriptions
   - ✅ Good: `{"bpm": 120.5, "is_steady": true, "tempo_stability_score": 0.91}`
   - ❌ Bad: `{"tempo": 120.5}` without context

7. **Error Handling**: Return structured errors that LLMs can reason about
   - ✅ Good: `{"error": true, "error_type": "TOO_SHORT", "message": "Audio is too short (minimum 0.5 seconds required)"}`
   - ❌ Bad: Generic exceptions or unclear error messages

## Baseline Tools (Always Run)

These tools are automatically called for every audio submission.

### `analyze_tempo(audio_file_id: str) -> dict`
**Purpose**: Detect tempo/BPM and timing consistency

**Returns**: BPM, confidence, is_steady, tempo_stability_score, tempo_changes, rushing_detected, dragging_detected

**Implementation**: librosa tempo detection and autocorrelation-based beat tracking

### `detect_pitch(audio_file_id: str) -> dict`
**Purpose**: Note-by-note pitch detection and intonation analysis

**Returns**: notes (with start_time, end_time, duration, pitch, frequency, confidence), intonation_accuracy, pitch_stability, detected_key, sharp_tendency, flat_tendency

**Implementation**: CREPE (deep learning) or PYIN for pitch tracking, with note segmentation via onset/offset detection

### `analyze_rhythm(audio_file_id: str) -> dict`
**Purpose**: Onset detection, timing accuracy, rhythmic patterns

**Returns**: onsets, timing_accuracy, rhythmic_pattern, is_on_beat, beat_deviations, average_deviation_ms, rushing_tendency, dragging_tendency

**Implementation**: librosa onset detection (spectral flux-based) and timing deviation analysis

## Optional Analysis Tools (LLM Decides)

### `detect_key(audio_file_id: str) -> dict`
**Returns**: key, confidence, mode, tonic

**Implementation**: Chroma-based key detection using librosa or music21 Krumhansl-Schmuckler algorithm

### `detect_chords(audio_file_id: str) -> dict`
**Returns**: chords (with time, duration, chord, confidence), progression

**Implementation**: Chroma feature extraction with template matching or music21 chord recognition

### `analyze_timbre(audio_file_id: str) -> dict`
**Returns**: brightness, warmth, sharpness, spectral_centroid, spectral_rolloff, spectral_bandwidth, timbre_consistency, attack_time, harmonic_ratio

**Implementation**: Spectral analysis using FFT/STFT, spectral centroid (brightness), rolloff, and harmonic-to-noise ratio

### `segment_phrases(audio_file_id: str) -> dict`
**Returns**: phrases (with start, end, type, confidence), phrase_count, average_phrase_length

**Implementation**: Energy-based segmentation with repetition detection and silence/pause analysis

### `comprehensive_analysis(audio_file_id: str) -> dict`
**Returns**: Structured summary with timing, pitch, dynamics, frequency (timbre), musical_structure (key, chords, phrases), articulation, overall_score, strengths, weaknesses, recommendations

**Note**: Runs all available analysis tools in parallel and provides comprehensive summary

### `analyze_groove(audio_file_id: str) -> dict`
**Returns**: groove_type ("straight" | "swung" | "reverse_swing"), swing_ratio, microtiming_pattern, feel_score, groove_consistency, average_microtiming_deviation_ms, microtiming_std_ms

**Implementation**: Microtiming histogram analysis and swing ratio calculation

### `detect_repetitions(audio_file_id: str) -> dict`
**Returns**: repetitions (with pattern_start, pattern_end, repetition_times, similarity), form

**Implementation**: Self-similarity matrix and pattern recognition via chroma features

### `analyze_dynamics(audio_file_id: str) -> dict`
**Returns**: average_rms, average_loudness, peak_amplitude, dynamic_range_db, dynamic_range, lufs, amplitude_envelope, dynamic_consistency, is_consistent, peaks

**Implementation**: RMS energy calculation, peak detection, and LUFS measurement

### `analyze_articulation(audio_file_id: str) -> dict`
**Returns**: articulation_types, legato_percentage, staccato_percentage, articulation_consistency, accents

**Implementation**: Note duration vs. inter-note gap analysis, energy envelope analysis, and pattern classification

## Comparison Tools

### `compare_audio(audio_file_id_1: str, audio_file_id_2: str, comparison_type: str) -> dict`
**Parameters**: `comparison_type`: "rhythm" | "pitch" | "tempo" | "overall" (default: "overall")

**Returns**: comparison_type, similarity_score (only for "overall"), differences (tempo, pitch_accuracy, pitch_stability, rhythm_accuracy, timing_deviation), improvements, regressions

### `compare_to_reference(audio_file_id: str, reference_type: str, reference_params: dict) -> dict`
**Parameters**:
- `reference_type`: "scale" | "midi_file"
- `reference_params`: For "scale": `{"scale": "C major", "tempo": 120}` (tempo optional), For "midi_file": `{"midi_file_id": "midi_123"}`

**Returns**: reference_type, comparison (pitch_accuracy, rhythm_accuracy, tempo_match), errors, detected_key (for scale)

## Audio Recording Tools

### `request_audio_recording(prompt: str, max_duration: float) -> dict`
**Parameters**: `prompt`: Instructions for what to record, `max_duration`: Maximum recording duration in seconds (optional, default: 60.0)

**Returns**: status ("recording_requested" | "completed"), prompt, max_duration, recording_id, audio_file_id (when completed), duration (when completed)

**UI Behavior**: When this tool is called, UI should show recording interface with the prompt displayed.

## MIDI Processing Tools

### `validate_midi(midi_text: str) -> dict`
**Returns**: valid, midi_file_id (if valid), errors, warnings, metadata (duration, tempo, tracks, note_count)

**Note**: LLM generates MIDI directly in its response. This tool validates and parses it.

### `midi_to_audio(midi_file_id: str, instrument: str) -> dict`
**Parameters**: `instrument`: "piano" | "guitar" | "violin" | "bass" | etc. (maps to FluidSynth soundfont)

**Returns**: audio_file_id, midi_file_id, instrument, duration, synthesis_method

**Note**: Uses FluidSynth for synthesis. Future: neural synthesis for better timbre/technique demonstration.

### `midi_to_notation(midi_file_id: str, format: str) -> dict`
**Parameters**: `format`: "sheet_music" | "tabs" | "both"

**Returns**: midi_file_id, sheet_music_url, tabs_url, format

## Utility Tools

### `get_audio_info(audio_file_id: str) -> dict`
**Returns**: duration, sample_rate, channels, format, file_size_bytes

### `segment_audio(audio_file_id: str, start_time: float, end_time: float) -> dict`
**Parameters**: `start_time`: >= 0, `end_time`: > start_time

**Returns**: new_audio_file_id, original_audio_file_id, start_time, end_time, duration

### `time_stretch(audio_file_id: str, rate: float) -> dict`
**Parameters**: `rate`: 0.25-4.0 (1.0 = no change, 0.5 = half speed, 2.0 = double speed)

**Returns**: new_audio_file_id, original_audio_file_id, rate, original_duration, new_duration

**Note**: Requires `pyrubberband` library. Useful for practice (slow down difficult passages) or demonstration (speed up).

### `pitch_shift(audio_file_id: str, semitones: float) -> dict`
**Parameters**: `semitones`: -24 to 24 (positive = higher, negative = lower)

**Returns**: new_audio_file_id, original_audio_file_id, semitones, duration

**Note**: Requires `pyrubberband` library. Useful for transposition or demonstrating different keys.

## Error Handling

All tools should return structured errors:
```json
{
  "error": true,
  "error_type": "INVALID_AUDIO" | "TOO_SHORT" | "PROCESSING_FAILED",
  "message": "Audio file is too short (minimum 0.5 seconds required)",
  "details": {}
}
```

## Implementation Libraries

**Core Libraries**:
- **librosa**: Comprehensive audio analysis (tempo, pitch, onset, chroma, MFCCs)
- **torchcrepe / crepe**: Deep learning pitch tracking (most accurate)
- **music21**: Music theory analysis (key detection, chord recognition)
- **pyrubberband**: Time-stretching and pitch-shifting
- **soundfile**: Audio file I/O
- **scipy**: Signal processing utilities
- **numpy**: Numerical operations

## Tool Discovery

Tool schemas are generated dynamically from code and injected into the system prompt at runtime.
