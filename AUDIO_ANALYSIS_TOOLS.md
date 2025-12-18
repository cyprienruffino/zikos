# Audio Analysis Tools Catalog

This document catalogs all signal processing and music analysis tools available for LLM-based audio understanding. The goal is to provide the LLM with comprehensive "hearing" capabilities through structured analysis tools.

## Design Philosophy

- **Instrument-Agnostic Core**: Most tools work across instruments, with instrument-specific extensions
- **Multi-Granularity**: Analysis at note-level, phrase-level, and overall performance
- **Structured Output**: All tools return JSON-serializable data that LLMs can reason about
- **Composable**: Tools can be combined for deeper insights
- **Extensible**: Easy to add new analysis dimensions

---

## Core Analysis Dimensions

### 1. Timing & Rhythm Analysis

#### 1.1 Tempo Detection
**Purpose**: Detect BPM and tempo stability

**Tools**:
- `analyze_tempo(audio_file_id)`
- `detect_tempo_changes(audio_file_id)`
- `analyze_tempo_stability(audio_file_id)`

**Techniques**:
- **librosa.beat.beat_track()**: Autocorrelation-based tempo detection
- **librosa.tempo()**: Multiple tempo estimation algorithms
- **madmom.features.beats.RNNBeatProcessor**: Deep learning beat tracking
- **Dynamic Time Warping (DTW)**: Compare against reference tempo

**Output Structure**:
```json
{
  "bpm": 120.5,
  "confidence": 0.92,
  "is_steady": true,
  "tempo_changes": [
    {"time": 0.0, "bpm": 120.0, "confidence": 0.95},
    {"time": 15.3, "bpm": 121.2, "confidence": 0.88}
  ],
  "tempo_stability_score": 0.91,
  "rushing_detected": false,
  "dragging_detected": false
}
```

#### 1.2 Beat Tracking
**Purpose**: Identify beat positions and grid alignment

**Tools**:
- `track_beats(audio_file_id)`
- `analyze_beat_alignment(audio_file_id, reference_bpm)`

**Techniques**:
- **librosa.beat.beat_track()**: Onset strength-based beat tracking
- **madmom**: RNN-based beat tracking
- **aubio.tempo()**: Real-time beat tracking

**Output Structure**:
```json
{
  "beats": [
    {"time": 0.0, "confidence": 0.94, "deviation_ms": 0},
    {"time": 0.5, "confidence": 0.91, "deviation_ms": -12}
  ],
  "beat_consistency": 0.87,
  "average_deviation_ms": -8.5,
  "grid_alignment_score": 0.89
}
```

#### 1.3 Onset Detection
**Purpose**: Detect note/event onsets with precise timing

**Tools**:
- `detect_onsets(audio_file_id)`
- `analyze_onset_strength(audio_file_id)`

**Techniques**:
- **librosa.onset.onset_detect()**: Spectral flux-based onset detection
- **librosa.onset.onset_strength()**: Onset strength function
- **aubio.onset()**: Real-time onset detection
- **madmom.features.onsets.CNNOnsetProcessor**: Deep learning onset detection

**Output Structure**:
```json
{
  "onsets": [
    {"time": 0.0, "confidence": 0.94, "strength": 0.87},
    {"time": 0.5, "confidence": 0.91, "strength": 0.82}
  ],
  "onset_count": 16,
  "average_onset_strength": 0.84,
  "weak_onsets": [{"time": 2.3, "strength": 0.45}]
}
```

#### 1.4 Timing Accuracy
**Purpose**: Measure timing precision relative to metronome or reference

**Tools**:
- `analyze_timing_accuracy(audio_file_id, reference_bpm)`
- `detect_timing_deviations(audio_file_id)`

**Techniques**:
- Inter-Onset Interval (IOI) analysis
- Deviation from metronome grid
- Timing variance calculation
- Microtiming analysis (swing, groove)

**Output Structure**:
```json
{
  "timing_accuracy_score": 0.87,
  "average_deviation_ms": -8.5,
  "deviation_std_ms": 12.3,
  "deviations": [
    {"time": 2.3, "deviation_ms": -15, "severity": "minor"},
    {"time": 5.1, "deviation_ms": 45, "severity": "major"}
  ],
  "rushing_tendency": 0.12,
  "dragging_tendency": 0.08
}
```

#### 1.5 Groove Analysis
**Purpose**: Analyze microtiming patterns and feel

**Tools**:
- `analyze_groove(audio_file_id)`
- `detect_swing_pattern(audio_file_id)`

**Techniques**:
- Microtiming histogram analysis
- Swing ratio calculation
- Groove template matching

**Output Structure**:
```json
{
  "groove_type": "straight",
  "swing_ratio": 1.0,
  "microtiming_pattern": "consistent",
  "feel_score": 0.89,
  "groove_consistency": 0.92
}
```

---

### 2. Pitch & Intonation Analysis

#### 2.1 Pitch Tracking
**Purpose**: Extract fundamental frequency over time

**Tools**:
- `track_pitch(audio_file_id)`
- `analyze_pitch_contour(audio_file_id)`

**Techniques**:
- **CREPE (torchcrepe)**: Deep learning pitch tracking (most accurate)
- **PYIN (librosa.pyin)**: Probabilistic YIN algorithm
- **YIN (aubio.pitch)**: Autocorrelation-based
- **pYIN**: Probabilistic extension of YIN
- **SWIPE**: Sawtooth Waveform Inspired Pitch Estimator

**Output Structure**:
```json
{
  "pitch_track": [
    {"time": 0.0, "frequency": 261.63, "confidence": 0.95, "pitch_class": "C", "octave": 4},
    {"time": 0.1, "frequency": 261.65, "confidence": 0.94, "pitch_class": "C", "octave": 4}
  ],
  "pitch_stability": 0.91,
  "pitch_range_hz": [82.41, 329.63],
  "pitch_range_notes": ["E2", "E4"]
}
```

#### 2.2 Note Segmentation
**Purpose**: Identify individual notes with boundaries

**Tools**:
- `segment_notes(audio_file_id)`
- `detect_note_boundaries(audio_file_id)`

**Techniques**:
- Onset + offset detection
- Pitch stability analysis
- Energy-based segmentation
- Combined onset/pitch analysis

**Output Structure**:
```json
{
  "notes": [
    {
      "start_time": 0.0,
      "end_time": 0.5,
      "duration": 0.5,
      "pitch": "C4",
      "frequency": 261.63,
      "confidence": 0.95,
      "onset_confidence": 0.94,
      "offset_confidence": 0.91
    }
  ],
  "note_count": 16,
  "average_note_duration": 0.5
}
```

#### 2.3 Intonation Analysis
**Purpose**: Measure pitch accuracy relative to equal temperament

**Tools**:
- `analyze_intonation(audio_file_id)`
- `detect_intonation_errors(audio_file_id)`

**Techniques**:
- Cents deviation from equal temperament
- Just intonation comparison
- Fret position estimation (for fretted instruments)
- Pitch histogram analysis

**Output Structure**:
```json
{
  "overall_intonation_score": 0.88,
  "average_cents_deviation": 8.5,
  "intonation_errors": [
    {
      "time": 2.3,
      "expected_pitch": "E4",
      "actual_frequency": 332.5,
      "cents_deviation": 15.2,
      "severity": "minor"
    }
  ],
  "sharp_tendency": 0.12,
  "flat_tendency": 0.08,
  "fret_accuracy": 0.91
}
```

#### 2.4 Pitch Stability
**Purpose**: Analyze pitch consistency during sustained notes

**Tools**:
- `analyze_pitch_stability(audio_file_id)`
- `detect_pitch_drift(audio_file_id)`

**Techniques**:
- Pitch variance during sustains
- Drift detection (sharpening/flattening)
- Vibrato analysis

**Output Structure**:
```json
{
  "pitch_stability_score": 0.91,
  "sustained_notes": [
    {
      "start_time": 0.0,
      "duration": 2.0,
      "pitch_variance_cents": 5.2,
      "drift_cents_per_second": 0.8,
      "has_vibrato": true
    }
  ],
  "average_pitch_variance": 6.3
}
```

#### 2.5 Vibrato Analysis
**Purpose**: Detect and characterize vibrato

**Tools**:
- `detect_vibrato(audio_file_id)`
- `analyze_vibrato_characteristics(audio_file_id)`

**Techniques**:
- Pitch modulation detection
- Vibrato rate (Hz) and depth (cents) calculation
- Vibrato consistency analysis

**Output Structure**:
```json
{
  "vibrato_detected": true,
  "vibrato_instances": [
    {
      "start_time": 1.0,
      "duration": 2.0,
      "rate_hz": 5.2,
      "depth_cents": 25.0,
      "consistency": 0.89
    }
  ],
  "average_rate_hz": 5.2,
  "average_depth_cents": 25.0
}
```

---

### 3. Dynamics & Articulation

#### 3.1 Amplitude Analysis
**Purpose**: Measure volume and dynamic range

**Tools**:
- `analyze_amplitude(audio_file_id)`
- `measure_dynamic_range(audio_file_id)`

**Techniques**:
- RMS (Root Mean Square) energy calculation
- Peak amplitude detection
- LUFS (Loudness Units Full Scale) measurement
- Dynamic range calculation (peak - RMS)

**Output Structure**:
```json
{
  "average_rms": -12.5,
  "peak_amplitude": -8.1,
  "dynamic_range_db": 15.3,
  "lufs": -14.2,
  "amplitude_envelope": [
    {"time": 0.0, "rms": -12.5, "peak": -8.1}
  ],
  "dynamic_consistency": 0.87
}
```

#### 3.2 Attack Analysis
**Purpose**: Characterize note attack transients

**Tools**:
- `analyze_attack_characteristics(audio_file_id)`
- `detect_attack_types(audio_file_id)`

**Techniques**:
- Attack time calculation (time to peak)
- Attack slope analysis
- Transient detection

**Output Structure**:
```json
{
  "average_attack_time_ms": 15.2,
  "attack_characteristics": [
    {
      "time": 0.0,
      "attack_time_ms": 12.5,
      "attack_slope": 0.87,
      "type": "sharp"
    }
  ],
  "attack_consistency": 0.89
}
```

#### 3.3 Sustain & Decay Analysis
**Purpose**: Analyze note sustain and decay envelopes

**Tools**:
- `analyze_sustain_decay(audio_file_id)`
- `measure_envelope_characteristics(audio_file_id)`

**Techniques**:
- ADSR envelope extraction
- Decay rate calculation
- Sustain level analysis

**Output Structure**:
```json
{
  "envelopes": [
    {
      "note_start": 0.0,
      "attack_ms": 15.2,
      "decay_ms": 50.3,
      "sustain_level": 0.75,
      "release_ms": 120.5
    }
  ],
  "average_sustain_level": 0.78,
  "decay_consistency": 0.85
}
```

#### 3.4 Accent Detection
**Purpose**: Identify accented notes

**Tools**:
- `detect_accents(audio_file_id)`
- `analyze_accent_patterns(audio_file_id)`

**Techniques**:
- Amplitude threshold analysis
- Relative loudness comparison
- Pattern recognition

**Output Structure**:
```json
{
  "accents": [
    {"time": 1.5, "intensity": 0.82, "relative_loudness": 1.25}
  ],
  "accent_count": 4,
  "accent_consistency": 0.78
}
```

#### 3.5 Articulation Types
**Purpose**: Classify staccato, legato, etc.

**Tools**:
- `classify_articulation(audio_file_id)`
- `analyze_articulation_patterns(audio_file_id)`

**Techniques**:
- Note duration vs. inter-note gap analysis
- Energy envelope analysis
- Pattern classification

**Output Structure**:
```json
{
  "articulation_types": ["legato", "staccato"],
  "legato_percentage": 0.65,
  "staccato_percentage": 0.35,
  "articulation_consistency": 0.82
}
```

---

### 4. Frequency Domain Analysis

#### 4.1 Spectral Characteristics
**Purpose**: Analyze frequency content and timbre

**Tools**:
- `analyze_spectrum(audio_file_id)`
- `extract_spectral_features(audio_file_id)`

**Techniques**:
- **FFT**: Fast Fourier Transform
- **STFT**: Short-Time Fourier Transform
- **Mel Spectrogram**: Mel-scaled frequency representation
- **MFCC**: Mel-Frequency Cepstral Coefficients
- **Chroma**: Pitch class representation

**Output Structure**:
```json
{
  "spectral_centroid": 2500.0,
  "spectral_rolloff": 5000.0,
  "spectral_bandwidth": 1500.0,
  "zero_crossing_rate": 0.12,
  "mfcc": [12.5, -3.2, 5.1, ...],
  "chroma": [0.85, 0.12, 0.45, ...]
}
```

#### 4.2 Harmonic Analysis
**Purpose**: Analyze harmonic content and overtones

**Tools**:
- `analyze_harmonics(audio_file_id)`
- `detect_harmonic_series(audio_file_id)`

**Techniques**:
- Harmonic-to-noise ratio (HNR)
- Harmonic partial detection
- Overtone analysis
- Spectral peak detection

**Output Structure**:
```json
{
  "harmonic_ratio": 0.85,
  "harmonic_partials": [
    {"frequency": 261.63, "amplitude": 0.95, "partial": 1},
    {"frequency": 523.26, "amplitude": 0.45, "partial": 2}
  ],
  "harmonic_richness": 0.78
}
```

#### 4.3 Timbre Analysis
**Purpose**: Characterize tone quality

**Tools**:
- `analyze_timbre(audio_file_id)`
- `extract_timbre_features(audio_file_id)`

**Techniques**:
- Spectral centroid (brightness)
- Spectral rolloff
- Spectral flux
- Brightness, warmth, sharpness metrics

**Output Structure**:
```json
{
  "brightness": 0.72,
  "warmth": 0.65,
  "sharpness": 0.58,
  "spectral_centroid": 2500.0,
  "timbre_consistency": 0.84
}
```

#### 4.4 Low-Frequency Analysis (Bass-Specific)
**Purpose**: Analyze sub-bass and low-end characteristics

**Tools**:
- `analyze_low_frequencies(audio_file_id)`
- `detect_muddiness(audio_file_id)`

**Techniques**:
- Sub-bass energy (20-60 Hz)
- Low-end presence (60-250 Hz)
- Frequency masking detection
- Clarity analysis

**Output Structure**:
```json
{
  "sub_bass_energy": 0.45,
  "low_end_presence": 0.78,
  "muddiness_score": 0.12,
  "clarity_score": 0.88,
  "frequency_mask_detected": false
}
```

---

### 5. Technique-Specific Analysis

#### 5.1 Finger Noise Detection (Bass/Guitar)
**Purpose**: Detect finger movement artifacts

**Tools**:
- `detect_finger_noise(audio_file_id)`
- `analyze_finger_technique(audio_file_id)`

**Techniques**:
- High-frequency artifact detection (2-8 kHz)
- Transient analysis
- Noise-to-signal ratio

**Output Structure**:
```json
{
  "finger_noise_detected": true,
  "noise_instances": [
    {"time": 1.2, "intensity": 0.35, "frequency_range": "2-5kHz"}
  ],
  "noise_to_signal_ratio": 0.08,
  "technique_cleanliness": 0.92
}
```

#### 5.2 Pick Attack Analysis (Bass/Guitar)
**Purpose**: Characterize pick attack characteristics

**Tools**:
- `analyze_pick_attack(audio_file_id)`
- `detect_pick_technique(audio_file_id)`

**Techniques**:
- Attack transient analysis
- Spectral analysis of attack
- Pick angle estimation (from spectral content)

**Output Structure**:
```json
{
  "pick_attack_detected": true,
  "attack_characteristics": {
    "sharpness": 0.85,
    "attack_time_ms": 8.5,
    "spectral_content": "bright"
  },
  "pick_consistency": 0.87
}
```

#### 5.3 Slap/Pop Detection (Bass)
**Purpose**: Identify slap and pop techniques

**Tools**:
- `detect_slap_pop(audio_file_id)`
- `analyze_slap_technique(audio_file_id)`

**Techniques**:
- Transient detection with specific characteristics
- Spectral signature analysis
- Energy envelope analysis

**Output Structure**:
```json
{
  "slap_detected": true,
  "pop_detected": true,
  "technique_instances": [
    {"time": 2.3, "type": "slap", "confidence": 0.92},
    {"time": 3.1, "type": "pop", "confidence": 0.88}
  ],
  "technique_consistency": 0.85
}
```

#### 5.4 Muting Analysis
**Purpose**: Assess muting effectiveness

**Tools**:
- `analyze_muting(audio_file_id)`
- `detect_unwanted_resonance(audio_file_id)`

**Techniques**:
- Unwanted string resonance detection
- Decay analysis
- Frequency analysis of muted vs. unmuted notes

**Output Structure**:
```json
{
  "muting_effectiveness": 0.88,
  "unwanted_resonance": [
    {"time": 1.5, "frequency": 220.0, "duration": 0.3, "severity": "minor"}
  ],
  "muting_consistency": 0.85
}
```

#### 5.5 String Crossing Analysis
**Purpose**: Detect artifacts from string changes

**Tools**:
- `analyze_string_crossing(audio_file_id)`
- `detect_crossing_artifacts(audio_file_id)`

**Techniques**:
- Timing inconsistencies at string changes
- Volume inconsistencies
- Frequency jumps analysis

**Output Structure**:
```json
{
  "string_crossing_detected": true,
  "crossing_artifacts": [
    {"time": 2.1, "type": "timing_inconsistency", "severity": "minor"},
    {"time": 3.5, "type": "volume_inconsistency", "severity": "moderate"}
  ],
  "crossing_smoothness": 0.82
}
```

#### 5.6 Plucking Position Estimation (Bass)
**Purpose**: Estimate where strings are plucked (bridge vs. neck)

**Tools**:
- `estimate_plucking_position(audio_file_id)`

**Techniques**:
- Spectral centroid analysis
- Harmonic content analysis
- Formant analysis

**Output Structure**:
```json
{
  "plucking_positions": [
    {"time": 0.0, "position": "bridge", "confidence": 0.85},
    {"time": 1.5, "position": "neck", "confidence": 0.78}
  ],
  "position_consistency": 0.80
}
```

---

### 6. Musical Structure Analysis

#### 6.1 Key Detection
**Purpose**: Identify musical key

**Tools**:
- `detect_key(audio_file_id)`
- `analyze_key_confidence(audio_file_id)`

**Techniques**:
- **librosa.key_to_notes()**: Chroma-based key detection
- **music21.analysis.discrete.KrumhanslSchmuckler**: Krumhansl-Schmuckler algorithm
- **Temperley's key-finding algorithm**
- Chroma profile matching

**Output Structure**:
```json
{
  "key": "C major",
  "confidence": 0.89,
  "mode": "major",
  "tonic": "C",
  "alternative_keys": [
    {"key": "A minor", "confidence": 0.75}
  ]
}
```

#### 6.2 Chord Detection
**Purpose**: Identify chord progressions

**Tools**:
- `detect_chords(audio_file_id)`
- `analyze_chord_progression(audio_file_id)`

**Techniques**:
- **librosa.chroma.chroma_stft()**: Chroma feature extraction
- **music21.analysis.chord**: Chord recognition
- Template matching
- Deep learning chord recognition

**Output Structure**:
```json
{
  "chords": [
    {"time": 0.0, "duration": 2.0, "chord": "Cmaj", "confidence": 0.93},
    {"time": 2.0, "duration": 2.0, "chord": "Amin", "confidence": 0.91}
  ],
  "progression": ["Cmaj", "Amin", "Fmaj", "Gmaj"],
  "progression_type": "I-vi-IV-V"
}
```

#### 6.3 Phrase Segmentation
**Purpose**: Identify musical phrase boundaries

**Tools**:
- `segment_phrases(audio_file_id)`
- `detect_phrase_boundaries(audio_file_id)`

**Techniques**:
- Energy-based segmentation
- Repetition detection
- Musical structure analysis
- Silence/pause detection

**Output Structure**:
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

#### 6.4 Repetition Detection
**Purpose**: Identify repeated patterns

**Tools**:
- `detect_repetitions(audio_file_id)`
- `analyze_musical_form(audio_file_id)`

**Techniques**:
- Self-similarity matrix
- Template matching
- Pattern recognition

**Output Structure**:
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

---

### 7. Comprehensive Analysis

#### 7.1 Full Analysis Pipeline
**Purpose**: Run all analyses and provide structured summary

**Tools**:
- `comprehensive_analysis(audio_file_id)`
- `get_analysis_summary(audio_file_id)`

**Output Structure**:
```json
{
  "timing": {...},
  "pitch": {...},
  "dynamics": {...},
  "frequency": {...},
  "technique": {...},
  "musical_structure": {...},
  "overall_score": 0.87,
  "strengths": ["timing", "intonation"],
  "weaknesses": ["dynamic_consistency", "finger_noise"],
  "recommendations": [...]
}
```

---

## Implementation Libraries

### Core Libraries
- **librosa**: Comprehensive audio analysis (tempo, pitch, onset, chroma, MFCCs)
- **torchaudio**: PyTorch-native audio I/O and processing
- **soundfile**: Audio file I/O
- **scipy**: Signal processing utilities
- **numpy**: Numerical operations

### Advanced Libraries
- **torchcrepe / crepe**: Deep learning pitch tracking
- **madmom**: Beat tracking, onset detection (deep learning)
- **aubio**: Real-time audio analysis
- **essentia**: Advanced audio analysis (C++/Python)
- **music21**: Music theory analysis

### Specialized Libraries
- **pyrubberband**: Time-stretching and pitch-shifting
- **pyAudioAnalysis**: Audio feature extraction
- **mir_eval**: Music information retrieval evaluation

---

## Tool Organization Strategy

### Baseline Tools (Always Run)
These provide fundamental analysis immediately after recording:
- `analyze_tempo()`
- `detect_pitch()`
- `analyze_rhythm()`

### Optional Tools (LLM Decides)
LLM calls these based on context:
- `analyze_dynamics()`
- `analyze_articulation()`
- `analyze_timbre()`
- `analyze_technique()` (instrument-specific)
- `detect_key()`
- `detect_chords()`
- `segment_phrases()`

### Comprehensive Tool
- `comprehensive_analysis()`: Runs all analyses in parallel

---

## Extensibility for Other Instruments

### Instrument-Specific Extensions

**Guitar**:
- Strumming pattern detection
- Fingerpicking pattern analysis
- Bending detection
- Slide detection
- Hammer-on/pull-off detection

**Piano**:
- Pedal usage detection
- Hand coordination analysis
- Voicing analysis
- Polyphonic note separation

**Drums**:
- Drum kit component identification
- Groove pattern analysis
- Ghost note detection
- Fill detection

**Voice**:
- Formant analysis
- Vibrato detection
- Breath control analysis
- Vocal range analysis

---

## Notes

- All tools should handle errors gracefully and return structured error responses
- Tools should validate audio quality (duration, sample rate, etc.)
- Consider caching intermediate results for efficiency
- Design for batch processing (POC), but keep architecture flexible for future streaming
