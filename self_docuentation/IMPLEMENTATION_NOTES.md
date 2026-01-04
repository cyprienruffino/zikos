# Implementation Notes & Status

## LLM Service Refactoring

### Status: ✅ Completed

**Problem**: `LLMService` was a 1300+ line god object with multiple responsibilities.

**Solution**: Extracted focused, testable components:
1. ✅ `ThinkingExtractor` - Extracts thinking from `<thinking>` tags
2. ✅ `ConversationManager` - Manages conversation history per session
3. ✅ `MessagePreparer` - Prepares messages, handles truncation, system prompt injection
4. ✅ `AudioContextEnricher` - Enriches messages with audio analysis context
5. ✅ `ToolInjector` - Injects tools into system prompts
6. ✅ `ToolCallParser` - Parses native and Qwen XML tool calls
7. ✅ `ToolExecutor` - Executes tools, handles errors, widget detection
8. ✅ `ResponseValidator` - Validates responses (gibberish, tokens, loops)
9. ✅ `LLMOrchestrator` - Orchestrates generate_response and generate_response_stream

**Location**: `backend/zikos/services/llm_orchestration/`

**Design Principles**:
- Single Responsibility: Each class has one clear purpose
- Testability: Components can be tested in isolation
- Reusability: Shared logic extracted to avoid duplication
- Backward Compatibility: Public API unchanged, internal refactoring only

**Constants Added** (to `backend/zikos/constants.py`):
- `MAX_CONSECUTIVE_TOOL_CALLS = 5`
- `RECENT_TOOL_CALLS_WINDOW = 10`
- `REPETITIVE_PATTERN_THRESHOLD = 4`

**Logging Migration**: ✅ Completed
- Replaced all `print()` statements with proper `logging.getLogger()` calls
- Appropriate log levels: `debug()`, `info()`, `warning()`, `error()`

## Music Flamingo Integration

### Status: ⏳ Planned

**Model**: `nvidia/music-flamingo-hf` (Audio Flamingo 3, 8B parameters)

**Key Constraints**:
- Max audio length: 20 minutes total
- Processing: 30-second windows
- Per-sample cap: 10 minutes (truncated if longer)
- Formats: WAV, MP3, FLAC
- Max input text: 24,000 tokens
- Max output text: 2,048 tokens

**Usage Pattern**:
```python
conversation = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "Analyze this performance"},
        {"type": "audio", "path": "/path/to/audio.wav"}
    ]
}]
```

**Implementation Considerations**:
1. New backend: `MusicFlamingoBackend` (or extend `TransformersBackend`)
2. Input format: Multimodal (text + audio paths)
3. Audio preprocessing: Format conversion, sample rate, duration handling
4. Tool calling: Verify if Music Flamingo supports function calling (CRITICAL)
5. Output limitations: 2,048 token max (may truncate detailed feedback)

**Recommended Approach**: Hybrid
- Qwen orchestrates tools and handles analysis
- Music Flamingo as sophisticated tool - can be called when needed
- Remote service option - Music Flamingo can run on dedicated service
- Benefits: Keeps existing architecture, leverages both signal processing and model predictions

**Challenges**:
- Tool calling support unknown (may need hybrid approach)
- Output token limit (2,048 vs current flexible length)
- Context window (24K tokens vs current 32K+)
- Audio preprocessing pipeline needed
- Higher VRAM requirements

## Prompt System Architecture

### Status: ✅ Completed

**Location**: `backend/zikos/services/prompt/`

**Structure**:
```
prompt/
├── __init__.py              # Public API exports
├── builder.py               # SystemPromptBuilder - composes sections
└── sections/
    ├── __init__.py          # Section exports
    ├── base.py              # PromptSection abstract base class
    ├── core.py              # CorePromptSection - loads from SYSTEM_PROMPT.md
    ├── music_flamingo.py    # MusicFlamingoSection - conditional Music Flamingo info
    ├── tools.py             # ToolInstructionsSection - dynamic tool documentation
    └── audio_context.py     # Audio analysis context formatters
```

**Key Components**:
- `PromptSection` base class: `render()` and `should_include()` methods
- `SystemPromptBuilder`: Composes sections, filters by `should_include()`
- `CorePromptSection`: Loads core prompt from SYSTEM_PROMPT.md
- `MusicFlamingoSection`: Conditionally includes Music Flamingo instructions
- `ToolInstructionsSection`: Dynamically generates tool documentation at runtime
- `AudioAnalysisContextFormatter`: Static methods for formatting analysis context

**Benefits**:
- Modular: Each section is self-contained and testable
- Composable: Easy to add/remove/reorder sections
- Type-safe: Clear interfaces and inheritance
- Maintainable: Changes localized to specific sections
- No scattered strings: All prompt content in prompt module

## Test Issues Fixed

### Status: ✅ Completed

**Issues Found**:
1. Wrong method being checked - Tests checked `create_chat_completion` but code uses `stream_chat_completion`
2. Weak assertions - Tests used `if call_args:` which silently passes if method wasn't called
3. Tests validate mocks, not behavior - Some tests just verify mocked responses were returned

**Fixes Applied**:
- Changed approach: Validate actual behavior by checking conversation history instead of mock internals
- Improved assertions: Check for specific markers like `[Audio Analysis Context]` or actual data
- Tests now properly validate behavior rather than just checking if mocks were called

**Files Fixed**: `tests/unit/test_llm_service.py`
