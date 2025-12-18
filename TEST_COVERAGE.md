# Test Coverage Status

## Current Test Coverage

### ✅ Tested Components

1. **Configuration** (`tests/unit/test_config.py`)
   - Settings defaults
   - Environment variable loading

2. **MCP Tools** (`tests/unit/test_mcp_tools.py`)
   - `analyze_tempo()` - Basic tempo analysis
   - `request_audio_recording()` - Recording request tool

3. **API Endpoints** (`tests/integration/test_api.py`)
   - Root endpoint
   - Health endpoint

## ❌ Missing Test Coverage

### Critical Components (No Tests)

1. **LLMService** (`src/zikos/services/llm.py`)
   - Tool call detection and execution loop
   - Conversation history management
   - System prompt loading
   - Tool argument parsing (JSON)
   - Handling of `request_audio_recording` tool calls
   - Error handling in tool execution
   - Maximum iterations handling

2. **ChatService** (`src/zikos/services/chat.py`)
   - `process_message()` - Message processing flow
   - `handle_audio_ready()` - Audio ready handling
   - Session creation and management
   - WebSocket disconnect handling

3. **AudioService** (`src/zikos/services/audio.py`)
   - `store_audio()` - Audio file storage
   - `run_baseline_analysis()` - Baseline analysis orchestration
   - `get_audio_info()` - Audio metadata retrieval
   - `get_audio_path()` - File path resolution

4. **MidiService** (`src/zikos/services/midi.py`)
   - `validate_midi()` - MIDI validation
   - `synthesize()` - MIDI to audio synthesis
   - `render_notation()` - MIDI to notation rendering
   - `get_midi_path()` - File path resolution

5. **WebSocket Endpoint** (`src/zikos/api/chat.py`)
   - WebSocket connection handling
   - Message type routing
   - Error handling
   - Disconnect handling

6. **Audio API** (`src/zikos/api/audio.py`)
   - Audio upload endpoint
   - Audio info endpoint
   - Audio file retrieval endpoint
   - Error handling

7. **MIDI API** (`src/zikos/api/midi.py`)
   - MIDI validation endpoint
   - MIDI synthesis endpoint
   - Notation rendering endpoint
   - MIDI file retrieval endpoint

8. **MCP Tools** (Partial coverage)
   - `detect_pitch()` - Not tested
   - `analyze_rhythm()` - Not tested
   - `get_audio_info()` - Not tested
   - All MIDI tools - Not tested

## Recommended Test Priorities

### High Priority (Core Functionality)

1. **LLMService tool call loop** - Critical for app functionality
2. **ChatService message processing** - Core user interaction
3. **AudioService baseline analysis** - Core feature
4. **WebSocket message routing** - Core communication

### Medium Priority

1. **AudioService storage operations**
2. **MidiService operations** (when implemented)
3. **Error handling across services**

### Low Priority

1. **Utility functions**
2. **Edge cases**
3. **Performance tests**

## Test Coverage Target

Current coverage: **~77%** (as of latest run)
Target coverage: **80%+** (as per project requirements)

**Note**: LLM service tests are excluded from coverage calculations as they are expensive and require model files. These tests are marked with `@pytest.mark.expensive` and `@pytest.mark.llama` and are skipped by default in CI.

## Notes

- Most new code added for tool calling is untested
- Integration tests for full flows are missing
- Mocking strategy needed for LLM calls (llama-cpp-python)
- WebSocket testing requires async test client setup
