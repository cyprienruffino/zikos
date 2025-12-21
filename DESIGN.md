# AI Music Teacher - Design Document

## Overview

A proof-of-concept AI music teacher that combines:
- **LLM chat interaction** for personalized, conversational teaching
- **Audio input analysis** using signal processing tools (librosa, soundfile)
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
- **FastAPI**: Web framework with WebSocket support
- **librosa**: Audio analysis (tempo, pitch, onset detection, chroma, MFCCs)
- **soundfile**: Audio file I/O (WAV, FLAC)
- **music21**: MIDI processing and notation rendering
- **pyfluidsynth**: MIDI to audio synthesis

#### LLM
- **Primary**: Qwen2.5-7B-Instruct or Qwen2.5-14B-Instruct (recommended for function calling)
- **Alternative**: Llama 3.2-8B-Instruct or Mistral-7B-Instruct-v0.3
- **Inference**:
  - `llama-cpp-python` for GGUF models (Qwen2.5, Llama, Mistral)
  - `transformers` for Qwen3 models (32B+)
- **Conditioning**:
  - **POC**: Tool-based via MCP (LLM calls audio analysis tools)
  - **Future**: Direct embedding conditioning via cross-attention layer
- **MIDI Generation**: LLM generates MIDI directly as text (validated via MCP tool)

#### Audio Generation
- **MIDI Generation**: LLM generates MIDI text → validated via `validate_midi()` tool
- **MIDI → Audio Synthesis**: FluidSynth (POC), neural synthesis (future for timbre/technique work)
- **Notation Rendering**: Music21 for backend rendering, VexFlow for frontend display

#### Frontend
- **TypeScript**: Frontend language
- **Web Audio API**: Audio recording and playback
- **WebSocket**: Real-time communication with backend

#### MCP Tools
- **Audio Recording**: `request_audio_recording()` - LLM requests user to record audio
- **Audio Analysis**: Tempo, pitch, rhythm, key, chords, timbre, dynamics, articulation
- **Comparison**: Compare two audios, compare to reference (scale, MIDI file)
- **MIDI**: Validate MIDI syntax, synthesize to audio, render notation
- **Widgets**: Metronome, tuner, chord progression, tempo trainer, ear trainer, practice timer

**Tool Output Requirements**: All analysis tools must return LLM-interpretable structured data:
- Normalized scores (0.0-1.0) where applicable
- Musical terminology (note names, chords, keys)
- Time references for all events/issues
- Severity indicators for problems
- Clear musical meaning (not raw signal processing values)
- See [TOOLS.md](./TOOLS.md) for detailed requirements

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
- Tool outputs are designed for LLM interpretation (see [TOOLS.md](./TOOLS.md))
- System prompt includes metric interpretation guidelines (see [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md))

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
- **Supported**: CPU-only, 8GB VRAM, 16GB VRAM, 24GB VRAM, 80GB+ VRAM (H100)
- **Recommended**: 8GB+ VRAM for best performance
- **Model Selection**: See [MODEL_RECOMMENDATIONS.md](./MODEL_RECOMMENDATIONS.md) and [CONFIGURATION.md](./CONFIGURATION.md)

## System Components

### 1. Audio Processing Service (MCP)
**Purpose**: Extract musical features from audio input

**Tools**:
- `analyze_tempo(audio_file_id)` - BPM detection and tempo stability
- `detect_pitch(audio_file_id)` - Note-by-note pitch analysis and intonation
- `analyze_rhythm(audio_file_id)` - Onset detection, timing accuracy
- `detect_key(audio_file_id)` - Musical key detection
- `detect_chords(audio_file_id)` - Chord progression analysis
- `analyze_timbre(audio_file_id)` - Spectral characteristics
- `analyze_dynamics(audio_file_id)` - Volume and dynamic range analysis
- `analyze_articulation(audio_file_id)` - Staccato, legato, accents
- `compare_audio(audio_file_id_1, audio_file_id_2)` - Compare two recordings
- `compare_to_reference(audio_file_id, reference_type, reference_params)` - Compare to scale or MIDI reference

**Implementation**: Python service exposing MCP-compatible endpoints

### 2. LLM Service
**Purpose**: Generate personalized teaching responses

**Model**: Qwen2.5-7B-Instruct (recommended) or Qwen2.5-14B-Instruct. Supports Qwen3-32B for high-end GPUs. Llama 3.2-8B and Mistral-7B as alternatives.

**Inference Engine**:
- `llama-cpp-python` for GGUF models (Qwen2.5, Llama, Mistral)
- `transformers` for Qwen3 models (32B+)

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

## Future Work & Roadmap

This section catalogs features and capabilities planned for future implementation beyond the POC phase.

### Source Separation & Reference Comparison

#### SAM-Audio Integration

**Purpose**: Isolate specific instrument parts from full song recordings for learning purposes.

**Use Case**: "Hey, here's a song by this band, could you help me learn the guitar part?"

**Technology**: [SAM-Audio](https://github.com/facebookresearch/sam-audio) by Meta Research

**Capabilities**:
- **Text Prompting**: "Extract the bass guitar from this song"
- **Visual Prompting**: Use video frames to isolate sounds associated with visual objects
- **Span Prompting**: Specify time ranges where target sound occurs
- **Re-ranking**: Multiple candidate generation with quality assessment

**Implementation Plan**:
1. Integrate SAM-Audio model (requires Hugging Face access)
2. Add source separation tool: `separate_instrument(audio_file_id, description)`
3. Add reference comparison tool: `compare_to_reference(audio_file_id, reference_audio_id)`
4. Build comparison analysis pipeline:
   - Extract target instrument from full song
   - Compare student performance to extracted reference
   - Provide detailed feedback on differences

**Tools to Add**:
- `separate_instrument(audio_file_id, description, prompt_type="text")`
- `compare_to_reference(audio_file_id, reference_audio_id, comparison_type="overall")`
- `extract_instrument_from_song(song_audio_id, instrument_description)`

**Challenges**:
- Model size and inference time
- Quality of separation (may need post-processing)
- Handling complex mixes
- Real-time vs. batch processing trade-offs

### Real-Time Processing

#### Streaming Audio Analysis

**Purpose**: Provide real-time feedback during performance

**Features**:
- Low-latency onset detection
- Real-time pitch tracking
- Live timing analysis
- Immediate feedback display

**Implementation**:
- WebSocket-based streaming
- Chunk-based processing
- Sliding window analysis
- Optimized algorithms for real-time constraints

**Tools**:
- `start_realtime_analysis(session_id)`
- `stream_audio_chunk(session_id, audio_chunk)`
- `get_realtime_feedback(session_id)`

### Advanced Model Training

#### CLAP Embedding Integration

**Purpose**: Direct audio understanding via semantic embeddings

**Approach**: Feed CLAP embeddings to LLM through cross-attention adapter

**Benefits**:
- More direct audio understanding
- Richer semantic representation
- Better context for LLM reasoning

**Implementation**:
- Fine-tune adapter layer for CLAP embeddings
- Integrate CLAP model (`laion/clap-htsat-fused`)
- Design embedding conditioning mechanism

#### Domain-Specific Fine-Tuning

**Purpose**: Improve LLM performance for music teaching domain

**Approaches**:
- LoRA fine-tuning for music teaching
- MIDI generation fine-tuning
- Music theory knowledge enhancement

**Data Requirements**:
- Curated music teaching conversations
- Audio analysis examples
- MIDI generation examples

### Enhanced Audio Analysis

#### Multi-Instrument Support

**Purpose**: Extend analysis tools to work with multiple instruments

**Instruments to Support**:
- Guitar (strumming, fingerpicking, bending, slides)
- Piano (pedal usage, hand coordination, voicing)
- Drums (kit components, groove patterns, fills)
- Voice (formants, vibrato, breath control)
- Wind instruments (breath control, embouchure)
- Strings (bowing techniques, vibrato)

**Implementation**:
- Instrument detection/classification
- Instrument-specific analysis pipelines
- Technique libraries per instrument

#### Advanced Technique Detection

**Bass**:
- Tapping
- Harmonics
- Double stops
- Walking bass patterns

**Guitar**:
- Fingerpicking patterns
- Strumming patterns
- Bending accuracy
- Slide techniques
- Hammer-on/pull-off detection

**Piano**:
- Pedal usage patterns
- Hand independence
- Voicing analysis
- Polyphonic complexity

### Progress Tracking & Curriculum

#### Learning Progress System

**Purpose**: Track student progress over time

**Features**:
- Historical performance comparison
- Skill level assessment
- Improvement metrics
- Personalized curriculum generation

**Implementation**:
- Database for session history
- Progress visualization
- Skill level tracking
- Adaptive difficulty

#### Personalized Curriculum

**Purpose**: Generate customized learning paths

**Features**:
- Skill gap identification
- Exercise recommendations
- Difficulty progression
- Practice schedule suggestions

### Enhanced MIDI Generation

#### Neural Audio Synthesis

**Purpose**: Better audio examples with realistic timbres

**Current**: FluidSynth (synthetic)
**Future**: Neural synthesis models for realistic instrument sounds

**Benefits**:
- More realistic examples
- Better technique demonstration
- Timbre-specific feedback

#### Advanced Notation Rendering

**Purpose**: Rich visual notation with technique markings

**Features**:
- Technique annotations (slap, pop, bend, etc.)
- Dynamic markings
- Articulation markings
- Fingering suggestions
- Tablature with technique indicators

### Multi-Modal Interaction

#### Text-to-Speech

**Purpose**: Voice interaction for hands-free learning

**Features**:
- Natural voice responses
- Pronunciation of musical terms
- Audio feedback narration

#### Video Analysis (Future)

**Purpose**: Analyze playing technique from video

**Features**:
- Hand position analysis
- Posture assessment
- Visual technique feedback
- Combined audio-visual analysis

**Technology**: SAM-Audio visual prompting, computer vision

### Integration & Platform Features

#### Music Learning Platform Integration

**Purpose**: Connect with existing learning platforms

**Integrations**:
- Music notation software (MuseScore, Sibelius)
- DAW integration (Reaper, Logic, etc.)
- Online learning platforms
- Sheet music databases

#### Community Features

**Purpose**: Social learning aspects

**Features**:
- Share performances
- Peer feedback
- Challenges and competitions
- Progress leaderboards

### Evaluation & Metrics

#### Teaching Effectiveness Metrics

**Purpose**: Measure and improve teaching quality

**Metrics**:
- Student improvement rates
- Engagement metrics
- Feedback quality scores
- Learning outcome tracking

#### A/B Testing Framework

**Purpose**: Test different teaching approaches

**Features**:
- Multiple prompt variations
- Teaching style experiments
- Feedback format testing
- Algorithm comparison

### Infrastructure Improvements

#### Performance Optimization

**Features**:
- Model quantization
- Caching strategies
- Distributed inference
- GPU optimization

#### Scalability

**Features**:
- Multi-user support
- Session management
- Resource pooling
- Load balancing

#### Monitoring & Logging

**Features**:
- Performance monitoring
- Error tracking
- Usage analytics
- Quality metrics

### Research & Experimental Features

#### Cross-Modal Learning

**Purpose**: Learn from audio + MIDI + notation simultaneously

**Approach**: Multi-modal embeddings and analysis

#### Style Transfer

**Purpose**: Demonstrate different playing styles

**Features**:
- Style analysis
- Style transfer examples
- Genre-specific feedback

#### Automatic Exercise Generation

**Purpose**: Generate practice exercises based on weaknesses

**Features**:
- Weakness detection
- Exercise generation
- Difficulty adaptation
- Progress tracking

### Priority Ranking

#### High Priority (Post-POC)
1. **SAM-Audio Integration** - Enables learning from songs
2. **Multi-Instrument Support** - Expands use cases
3. **Progress Tracking** - Core learning feature
4. **Real-Time Processing** - Better user experience

#### Medium Priority
1. CLAP Embedding Integration
2. Neural Audio Synthesis
3. Advanced Technique Detection
4. Personalized Curriculum

#### Low Priority (Research)
1. Video Analysis
2. Cross-Modal Learning
3. Style Transfer
4. Community Features

### Implementation Notes

- All future features should maintain backward compatibility
- Design for extensibility from the start
- Consider performance implications early
- Plan for gradual rollout and testing
- Document API changes and migrations

### References

- [SAM-Audio](https://github.com/facebookresearch/sam-audio) - Meta Research
- [CLAP](https://github.com/LAION-AI/CLAP) - LAION Audio-Visual Embeddings
- [Music21](https://web.mit.edu/music21/) - Music Analysis Framework
- [librosa](https://librosa.org/) - Audio Analysis Library

## Implementation Status

### ✅ Completed
- Project structure and MCP server implementation
- Audio analysis tools (tempo, pitch, rhythm, key, chords, timbre, dynamics, articulation)
- Audio recording tool with WebSocket integration
- MIDI validation, synthesis, and notation rendering
- LLM service with function calling support
- Web UI with chat, audio recording, and widget support
- Widget tools (metronome, tuner, chord progression, tempo trainer, ear trainer, practice timer)
- Comparison tools (compare_audio, compare_to_reference)
- End-to-end integration and testing

### 🔄 Future Enhancements
See "Future Work & Roadmap" section above for planned features including:
- CLAP embedding integration for direct audio understanding
- Real-time streaming analysis
- Multi-instrument support
- Progress tracking and curriculum

## Potential Challenges

1. **MIDI Generation Quality**: LLM may generate invalid or musically incoherent MIDI - validation tool helps but may need refinement
2. **Tool Selection**: LLM must correctly choose which tools to call - may miss issues if wrong tools called
3. **Audio Recording UX**: Need smooth integration between tool calls and UI recording interface
4. **Context Management**: Multiple audio submissions in conversation - need to track which audio is which
5. **MIDI Format Complexity**: Standard MIDI is complex - may need simplified format or good examples in system prompt

## Success Criteria (POC)

- [x] System can accept audio input and generate relevant feedback
- [x] LLM responses are contextually appropriate to audio analysis
- [x] MIDI generation produces usable musical examples
- [x] UI allows smooth interaction flow
- [x] System demonstrates personalized teaching behavior

## Current Status

The POC is functional with all core features implemented:
- ✅ MCP server with comprehensive audio analysis tools
- ✅ LLM service with function calling (llama-cpp-python)
- ✅ Audio recording and baseline analysis
- ✅ MIDI generation, validation, synthesis, and notation rendering
- ✅ Interactive practice widgets
- ✅ Web UI with chat, recording, and widget support
- ✅ Comprehensive test coverage (80%+)

See "Future Work & Roadmap" section above for planned enhancements.
