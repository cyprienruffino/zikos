# AI Music Teacher - Design Document

## Overview

A proof-of-concept AI music teacher that combines:
- **LLM chat interaction** for personalized, conversational teaching
- **Audio input analysis** using CLAP embeddings and signal processing
- **Intelligent agent behavior** to diagnose issues and suggest exercises
- **MIDI generation + synthesis** for audio examples and visual notation (sheet music/tabs)

## Core Architecture

### High-Level Flow

**Approach A: Tool-based (POC)**
```
User starts conversation
    ↓
LLM requests audio recording via MCP tool → UI shows recording interface
    ↓
User records audio → Audio uploaded and stored
    ↓
Baseline tools automatically run (tempo, pitch, rhythm analysis)
    ↓
LLM receives analysis results + chat history
    ↓
LLM calls additional MCP tools if needed → Gets structured analysis
    ↓
LLM reasons about analysis using its existing knowledge → Generates personalized feedback
    ↓
Optional: LLM generates MIDI directly → Validate MIDI → Synthesize audio + render notation
```

**Approach B: Embedding-based (Future)**
```
User Audio Input
    ↓
CLAP Encoder → Generate semantic embeddings
    ↓
Embeddings fed to LLM via cross-attention layer → Direct conditioning
    ↓
LLM generates personalized feedback
    ↓
Optional: MIDI Generation → Synthesize audio examples + generate notation
```

### Technology Stack

#### Backend
- **FastAPI**: Web framework with WebSocket support for future real-time features
- **PyTorch**: For CLAP model inference
- **Transformers**: CLAP model loading (`laion/clap-htsat-fused`)
- **librosa**: Audio analysis (tempo, pitch, onset detection, chroma, MFCCs)
- **torchaudio**: PyTorch-native audio I/O and processing
- **soundfile**: Audio file I/O (WAV, FLAC)

#### LLM
- **Primary**: Llama 3.1 8B-Instruct or Llama 3.2 8B-Instruct
- **Inference**: llama.cpp for efficient serving
- **Conditioning**:
  - **POC**: Tool-based via MCP (LLM calls audio analysis tools)
  - **Future**: Direct embedding conditioning via cross-attention layer
- **MIDI Generation**: LLM generates MIDI directly as text (validated via MCP tool)

#### Audio Generation
- **MIDI Generation**: LLM generates MIDI text → validated via `validate_midi()` tool
- **MIDI → Audio Synthesis**: FluidSynth (POC), neural synthesis (future for timbre/technique work)
- **Notation Rendering**: Music21 for backend rendering, VexFlow for frontend display

#### Frontend
- **React/Vue**: Web UI framework
- **Web Audio API**: Audio recording and playback
- **WebSocket**: For future real-time updates (batch for POC)

#### MCP Tools
- **Audio Recording**: `request_audio_recording()` - LLM requests user to record audio
- **Audio Analysis**: Tempo, pitch, rhythm, key, chords, timbre, dynamics, articulation
- **Comparison**: Compare two audios, compare to reference
- **MIDI**: Generate MIDI (LLM), validate MIDI syntax, synthesize to audio, render notation
- **Utility**: Audio info, segmentation

## Implementation Decisions

### Conditioning Strategy

#### Phase 1: Tool-based (POC)
- **Approach**: LLM acts as agent, uses MCP tools to interact with user and analyze audio
- **Method**:
  1. LLM requests audio recording via `request_audio_recording()` tool
  2. UI shows recording interface, user records audio
  3. Audio uploaded and stored, baseline tools automatically run (tempo, pitch, rhythm)
  4. LLM receives baseline analysis + chat history
  5. LLM autonomously calls additional MCP tools if needed (`detect_key`, `detect_chords`, etc.)
  6. LLM receives structured analysis results
  7. LLM reasons about results using its existing music knowledge
  8. LLM generates personalized feedback and suggestions
  9. Optional: LLM generates MIDI directly as text, validates via `validate_midi()`, synthesizes and renders notation

**Advantages**:
- No knowledge base needed (LLM has music theory knowledge)
- Interpretable (can see which tools LLM calls)
- Flexible (LLM decides what to analyze)
- No training required

#### Phase 2: Embedding-based (Future)
- **Approach**: Direct CLAP embedding conditioning via cross-attention
- **Method**:
  1. CLAP encodes audio → embeddings
  2. Embeddings fed to LLM through trained cross-attention adapter
  3. LLM processes embeddings alongside text tokens
  4. Requires fine-tuning adapter layer

### Processing Mode
- **POC**: Batch processing (no real-time requirements)
- **Future**: Streaming/real-time processing

### Audio Output
- **MIDI generation**: Yes (for musical examples)
- **MIDI → Audio synthesis**: Yes
- **Notation display**: Yes (sheet music/tabs in UI)
- **Text-to-speech**: No (for POC)

### Hardware
- **POC**: H100/H200 cloud instances
- **Future**: TBD based on performance requirements

## System Components

### 1. Audio Processing Service (MCP)
**Purpose**: Extract musical features from audio input

**Tools**:
- `analyze_tempo(audio) → float` - BPM detection
- `detect_pitch(audio) → List[Note]` - Note-by-note pitch analysis
- `analyze_rhythm(audio) → RhythmAnalysis` - Onset detection, timing accuracy
- `detect_key(audio) → Key` - Musical key detection
- `detect_chords(audio) → List[Chord]` - Chord progression analysis
- `segment_phrases(audio) → List[Segment]` - Musical phrase boundaries
- `analyze_timbre(audio) → TimbreFeatures` - Spectral characteristics
- `find_similar_audio(audio, database) → List[SimilarAudio]` - CLAP-based similarity

**Implementation**: Python service exposing MCP-compatible endpoints

### 2. LLM Service
**Purpose**: Generate personalized teaching responses

**Model**: Llama 3.1/3.2 8B-Instruct
**Inference Engine**: llama.cpp

**MIDI Generation**: LLM generates MIDI directly as text in its response. MIDI is extracted, validated via `validate_midi()` tool, then synthesized and rendered.

**Prompt Structure**: See SYSTEM_PROMPT.md for detailed system prompt

### 3. MIDI Processing Service
**Purpose**: Validate, synthesize, and render MIDI generated by LLM

**Components**:
- **MIDI Validation**: Parse and validate MIDI syntax from LLM output
- **MIDI → Audio**: FluidSynth synthesis (POC), neural synthesis (future)
- **MIDI → Notation**: Music21 for backend rendering, VexFlow for frontend

**Flow**:
1. LLM generates MIDI text in response
2. Extract MIDI from LLM output
3. Validate via `validate_midi()` tool
4. If valid: synthesize to audio, render notation
5. Return audio file + notation images to UI

### 4. Web UI
**Purpose**: User interface for interaction

**Features**:
- Audio recording (Web Audio API)
- Chat interface
- Audio playback
- Sheet music/tab display
- Exercise visualization

**Stack**: React/Vue + Web Audio API + WebSocket (for future)

## Data Flow

### Agent-Driven Interaction Flow
1. User starts conversation with text message
2. LLM processes message, decides to request audio via `request_audio_recording()` tool
3. UI receives tool call, shows recording interface
4. User records audio → uploaded to backend, stored with unique ID
5. Backend automatically runs baseline tools:
   - `analyze_tempo(audio_file_id)`
   - `detect_pitch(audio_file_id)`
   - `analyze_rhythm(audio_file_id)`
6. Baseline analysis results injected into LLM context
7. LLM processes analysis, may call additional tools:
   - `detect_key()`, `detect_chords()`, `analyze_timbre()`, etc.
8. LLM generates response with feedback
9. If LLM generates MIDI in response:
   - Extract MIDI text from response
   - Call `validate_midi(midi_text)` tool
   - If valid: call `midi_to_audio()` and `midi_to_notation()`
   - Return audio + notation to UI
10. UI displays response, audio playback, notation images

## Future Work / "Do Later"

See [FUTURE_FEATURES.md](./FUTURE_FEATURES.md) for comprehensive future features roadmap, including:
- Source separation with SAM-Audio for learning from songs
- Real-time processing capabilities
- Multi-instrument support
- Progress tracking and curriculum
- Advanced model training
- And more...

### Quick Reference

**High Priority**:
- [ ] SAM-Audio integration for source separation
- [ ] Multi-instrument analysis support
- [ ] Progress tracking system
- [ ] Real-time processing

**Medium Priority**:
- [ ] CLAP embedding integration
- [ ] Neural audio synthesis
- [ ] Advanced technique detection
- [ ] Personalized curriculum

See [FUTURE_FEATURES.md](./FUTURE_FEATURES.md) for detailed roadmap.

## Open Questions

1. **MIDI Format**: What MIDI format should LLM generate? (Standard MIDI file format, MusicXML, or simplified text format?)
2. **MIDI Validation**: How strict should validation be? Accept partial/incomplete MIDI?
3. **Audio Recording UX**: How to handle recording state in UI? Show recording button when tool is called?
4. **Tool Call Format**: How should LLM format tool calls? JSON? Function calling format?
5. **Evaluation Strategy**: How to measure POC success before retraining?

## Potential Challenges

1. **MIDI Generation Quality**: LLM may generate invalid or musically incoherent MIDI - validation tool helps but may need refinement
2. **Tool Selection**: LLM must correctly choose which tools to call - may miss issues if wrong tools called
3. **Audio Recording UX**: Need smooth integration between tool calls and UI recording interface
4. **Context Management**: Multiple audio submissions in conversation - need to track which audio is which
5. **MIDI Format Complexity**: Standard MIDI is complex - may need simplified format or good examples in system prompt

## Success Criteria (POC)

- [ ] System can accept audio input and generate relevant feedback
- [ ] LLM responses are contextually appropriate to audio analysis
- [ ] MIDI generation produces usable musical examples
- [ ] UI allows smooth interaction flow
- [ ] System demonstrates personalized teaching behavior

## Next Steps

1. Set up project structure
2. Implement MCP server with audio analysis tools
3. Implement audio recording tool (`request_audio_recording`)
4. Set up LLM service (llama.cpp) with system prompt
5. Implement MIDI validation, synthesis, and notation rendering tools
6. Build minimal web UI (chat + audio recording + playback + notation display)
7. Wire LLM to MCP tools
8. End-to-end integration and testing
