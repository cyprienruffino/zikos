# Architecture & Design Decisions

## Core Architecture

### Current Approach: Tool-Based (POC)
- LLM acts as agent, uses MCP tools to interact with user and analyze audio
- Flow: User message → LLM requests audio → Audio uploaded → Baseline tools run → LLM receives analysis → LLM calls additional tools if needed → LLM generates feedback
- Advantages: No training needed, interpretable, flexible, LLM has music knowledge
- Tool outputs designed for LLM interpretation (structured, normalized, musical terminology)

### Future Approach: Embedding-Based
- CLAP encoder → semantic embeddings → cross-attention to LLM
- Requires fine-tuning adapter layer
- More direct audio understanding

## Technology Stack

### Backend
- FastAPI: Web framework with WebSocket support
- librosa: Audio analysis (tempo, pitch, onset, chroma, MFCCs)
- soundfile: Audio file I/O (WAV, FLAC)
- music21: MIDI processing and notation rendering
- pyfluidsynth: MIDI to audio synthesis

### LLM
- Primary: Qwen2.5-7B/14B-Instruct (function calling optimized)
- High-end: Qwen3-32B-Instruct (H100 GPUs)
- Inference: `llama-cpp-python` (GGUF) or `transformers` (Qwen3)
- MIDI Generation: LLM generates MIDI as text, validated via `validate_midi()` tool

### Frontend
- TypeScript: Frontend language
- Web Audio API: Audio recording and playback
- WebSocket: Real-time communication

## System Components

### 1. Audio Processing Service (MCP)
**Location**: `backend/zikos/mcp/tools/processing/audio/`

**Baseline Tools** (auto-run on upload):
- `analyze_tempo()` - BPM detection and tempo stability
- `detect_pitch()` - Note-by-note pitch analysis
- `analyze_rhythm()` - Onset detection, timing accuracy

**Optional Tools** (LLM decides):
- `detect_key()`, `detect_chords()`, `analyze_timbre()`, `analyze_dynamics()`, `analyze_articulation()`, `segment_phrases()`, `comprehensive_analysis()`, `analyze_groove()`, `detect_repetitions()`

**Comparison Tools**:
- `compare_audio()` - Compare two recordings
- `compare_to_reference()` - Compare to scale or MIDI reference

### 2. LLM Service
**Location**: `backend/zikos/services/llm.py`

**Architecture**: Refactored from god object to modular components:
- `ThinkingExtractor` - Extracts thinking from `<thinking>` tags
- `ConversationManager` - Manages conversation history per session
- `MessagePreparer` - Prepares messages, handles truncation
- `AudioContextEnricher` - Enriches messages with audio analysis context
- `ToolInjector` - Injects tools into system prompts
- `ToolCallParser` - Parses native and Qwen XML tool calls
- `ToolExecutor` - Executes tools via MCP server
- `ResponseValidator` - Validates responses (gibberish, tokens, loops)
- `LLMOrchestrator` - Orchestrates response generation

**Model**: Qwen2.5-7B-Instruct (recommended) or Qwen2.5-14B-Instruct. Supports Qwen3-32B for high-end GPUs.

**MIDI Generation**: LLM generates MIDI directly as text in response. MIDI extracted, validated via `validate_midi()`, then synthesized and rendered.

### 3. Prompt System
**Location**: `backend/zikos/services/prompt/`

**Modular Architecture**:
- `SystemPromptBuilder` - Composes sections
- `CorePromptSection` - Loads from SYSTEM_PROMPT.md
- `MusicFlamingoSection` - Conditional Music Flamingo info
- `ToolInstructionsSection` - Dynamic tool documentation
- `AudioAnalysisContextFormatter` - Formats analysis context messages

**Design Principles**:
- All prompt content in `prompt` module, never scattered
- Sections can be conditional
- Dynamic content injected via specialized sections/formatters

### 4. MIDI Processing Service
**Location**: `backend/zikos/services/midi.py`, `backend/zikos/mcp/tools/processing/midi/`

**Flow**:
1. LLM generates MIDI text in response
2. Extract MIDI from LLM output
3. Validate via `validate_midi()` tool
4. If valid: synthesize to audio, render notation
5. Return audio file + notation images to UI

**Components**:
- MIDI Validation: Parse and validate MIDI syntax
- MIDI → Audio: FluidSynth synthesis (POC), neural synthesis (future)
- MIDI → Notation: Music21 for backend rendering, VexFlow for frontend

### 5. Web UI
**Location**: `frontend/`

**Features**:
- Audio recording (Web Audio API)
- Chat interface
- Audio playback
- Sheet music/tab display
- Exercise visualization

## Data Flow

### Agent-Driven Interaction
1. User sends text message
2. LLM processes, decides to request audio via `request_audio_recording()` tool
3. UI shows recording interface
4. User records → uploaded to backend, stored with unique ID
5. Backend auto-runs baseline tools: `analyze_tempo()`, `detect_pitch()`, `analyze_rhythm()`
6. Baseline analysis injected into LLM context
7. LLM may call additional tools: `detect_key()`, `detect_chords()`, etc.
8. LLM generates response with feedback
9. If LLM generates MIDI: extract → validate → synthesize → render notation
10. UI displays response, audio playback, notation images

## Implementation Status

### ✅ Completed
- MCP server with comprehensive audio analysis tools
- LLM service with function calling (llama-cpp-python)
- Audio recording and baseline analysis
- MIDI generation, validation, synthesis, notation rendering
- Interactive practice widgets
- Web UI with chat, recording, widget support
- Comprehensive test coverage (80%+)
- Modular prompt system
- LLM service refactoring (extracted orchestration components)

### 🔄 Future Enhancements
- CLAP embedding integration for direct audio understanding
- Real-time streaming analysis
- Multi-instrument support
- Progress tracking and curriculum
- SAM-Audio integration for source separation
- Neural audio synthesis (better timbre/technique demonstration)

## Potential Challenges

1. **MIDI Generation Quality**: LLM may generate invalid MIDI - validation tool helps but may need refinement
2. **Tool Selection**: LLM must correctly choose which tools to call
3. **Audio Recording UX**: Need smooth integration between tool calls and UI recording interface
4. **Context Management**: Multiple audio submissions in conversation - need to track which audio is which
5. **MIDI Format Complexity**: Standard MIDI is complex - may need simplified format or good examples in system prompt

## Future Work

### High Priority
- SAM-Audio Integration - Enables learning from songs
- Multi-Instrument Support - Expands use cases
- Progress Tracking - Core learning feature
- Real-Time Processing - Better user experience

### Medium Priority
- CLAP Embedding Integration
- Neural Audio Synthesis
- Advanced Technique Detection
- Personalized Curriculum

### Low Priority (Research)
- Video Analysis
- Cross-Modal Learning
- Style Transfer
- Community Features
