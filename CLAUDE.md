# Zikos - Agent Reference

## Quick Reference

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && pre-commit install

# Testing
pytest                  # Unit tests with coverage (default)
pytest --no-cov         # Without coverage
pytest -k "pattern"     # Specific tests
pytest -m integration   # Integration tests
pytest -m comprehensive # LLM/heavy tests (excluded from CI)

# Code Quality
ruff check . && ruff format --check . && mypy backend/
```

---

## Architecture

### Core Flow
```
User message → LLM decides to request audio → User records →
Baseline tools auto-run (tempo, pitch, rhythm) → LLM receives analysis →
LLM calls additional tools if needed → LLM generates feedback →
If MIDI generated: validate → synthesize → render notation → UI displays
```

### Component Locations

| Component | Location |
|-----------|----------|
| **LLM Service** | `backend/zikos/services/llm.py` |
| **Orchestration** | `backend/zikos/services/llm_orchestration/` |
| | - `conversation_manager.py` - History per session |
| | - `message_preparer.py` - Truncation, system prompt |
| | - `audio_context_enricher.py` - Inject analysis |
| | - `tool_call_parser.py` - Parse native + Qwen XML |
| | - `tool_executor.py` - Execute via MCP |
| | - `response_validator.py` - Gibberish, tokens, loops |
| **Prompt System** | `backend/zikos/services/prompt/` |
| | - `builder.py` - Composes sections |
| | - `sections/core.py` - Loads SYSTEM_PROMPT.md |
| | - `sections/tools.py` - Dynamic tool docs |
| **Audio Tools** | `backend/zikos/mcp/tools/audio/` |
| **MIDI Tools** | `backend/zikos/mcp/tools/processing/midi/` |
| **LLM Backends** | `backend/zikos/services/llm_backends/` |
| **Frontend** | `frontend/src/` |
| **Tests** | `tests/unit/`, `tests/integration/`, `tests/comprehensive/` |

### Tech Stack
- **Backend**: FastAPI, librosa, soundfile, music21, pyfluidsynth
- **LLM**: Qwen2.5-7B/14B (recommended), llama-cpp-python or transformers
- **Frontend**: TypeScript, Web Audio API, WebSocket

---

## Tools Reference

### Design Principles for Tool Outputs
Tools return **LLM-interpretable** structured data:
1. **Musical context**: Metrics have clear musical meaning (not raw FFT)
2. **Normalized scores**: 0.0-1.0, higher = better
3. **Musical terminology**: Note names, chord names, keys (not just frequencies)
4. **Time references**: Precise locations for all events/issues
5. **Severity indicators**: Context for problems
6. **Structured errors**: `{"error": true, "error_type": "...", "message": "..."}`

### Baseline Tools (auto-run on upload)
- `analyze_tempo()` - BPM, stability, rushing/dragging
- `detect_pitch()` - Note-by-note, intonation, key detection
- `analyze_rhythm()` - Onsets, timing accuracy, beat deviations

### Optional Tools (LLM decides)
- `detect_key()`, `detect_chords()`, `analyze_timbre()`, `analyze_dynamics()`
- `analyze_articulation()`, `segment_phrases()`, `analyze_groove()`, `detect_repetitions()`
- `comprehensive_analysis()` - Runs all tools, provides summary

### Comparison Tools
- `compare_audio(id1, id2, type)` - Compare two recordings
- `compare_to_reference(id, ref_type, params)` - Compare to scale/MIDI

### MIDI Tools
- `validate_midi(text)` - Parse and validate LLM-generated MIDI
- `midi_to_audio(id, instrument)` - FluidSynth synthesis
- `midi_to_notation(id, format)` - Sheet music or tabs

### Utility Tools
- `request_audio_recording(prompt, max_duration)` - Trigger UI recording
- `get_audio_info(id)`, `segment_audio(id, start, end)`
- `time_stretch(id, rate)`, `pitch_shift(id, semitones)`

---

## Configuration

### Key Environment Variables
```bash
LLM_MODEL_PATH=./models/model.gguf  # Required
LLM_BACKEND=auto                     # auto|llama_cpp|transformers
LLM_N_GPU_LAYERS=-1                  # -1=full GPU, 0=CPU
LLM_N_CTX=                           # Auto-detected if not set
SYSTEM_PROMPT_CACHE_PATH=            # Optional KV cache
DEBUG_TOOL_CALLS=false               # Verbose tool logs
```

### Model Selection
| Hardware | Recommended Model | Config |
|----------|------------------|--------|
| CPU-only | Phi-3 Mini 4K Q4 (~2.3GB) | `LLM_N_GPU_LAYERS=0` |
| 8GB VRAM | Mistral 7B v0.3 Q4_K_M | `LLM_N_GPU_LAYERS=-1` |
| 16GB+ VRAM | Qwen2.5-14B Q4_K_M | `LLM_N_GPU_LAYERS=-1` |
| 80GB+ VRAM | Qwen3-32B (transformers) | `LLM_BACKEND=transformers` |

---

## Test Organization

- **Unit tests** (`tests/unit/`): Fast, mocked external deps, run in pre-commit
- **Integration tests** (`tests/integration/`): Test component interactions
- **Comprehensive tests** (`tests/comprehensive/`): Require real LLM/heavy audio, marked `@pytest.mark.comprehensive`

### Coverage Exclusions (require real models/hardware)
- `services/llm.py`, `llm_backends/*`, `utils/gpu.py`, `utils/context_length.py`

---

## Key Design Decisions

1. **Tool-based approach**: LLM acts as agent using MCP tools (no training needed, interpretable)
2. **Baseline + optional tools**: Auto-run essentials, LLM decides on extras
3. **MIDI as text**: LLM generates MIDI directly, validated via tool
4. **Modular LLM service**: Extracted from god object to testable components
5. **Prompt sections**: Composable, conditional sections for different contexts
6. **Token budget utilities**: Proportional reserves based on actual context window

## Known Constraints

- MIDI generation quality varies - validation tool helps but may need refinement
- Context management for multiple audio submissions needs care
- Small context windows (2K) require condensed prompts and aggressive truncation
