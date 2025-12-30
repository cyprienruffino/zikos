# Music Flamingo Implementation Notes

Based on the [HuggingFace model page](https://huggingface.co/nvidia/music-flamingo-hf), here are key considerations for implementation:

## Model Architecture

- **Model**: `nvidia/music-flamingo-hf`
- **Architecture**: Audio Flamingo 3 (8B parameters)
  - AF-Whisper unified audio encoder
  - MLP-based audio adaptor
  - Qwen2.5-7B decoder-only LLM backbone
- **Input**: Music (song/instrumental) + Text
- **Output**: Text (UTF-8 string)

## Key Constraints

### Audio Processing
- **Max audio length**: 20 minutes total
- **Processing**: 30-second windows
- **Per-sample cap**: 10 minutes (longer inputs are truncated)
- **Formats**: WAV, MP3, FLAC
- **Audio can be**: Local file path or URL

### Text Processing
- **Max input text**: 24,000 tokens
- **Max output text**: 2,048 tokens

## Usage Patterns

### 1. Single-turn: Audio + Text Instruction
```python
conversation = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this track in full detail..."},
            {"type": "audio", "path": "/path/to/audio.mp3"},
        ],
    }
]
```

### 2. Text-only Prompts
```python
conversation = [
    {"role": "user", "content": [{"type": "text", "text": "What is the capital of France?"}]}
]
```

### 3. Audio-only Prompts
```python
conversation = [
    {"role": "user", "content": [{"type": "audio", "path": "/path/to/audio.wav"}]}
]
```

### 4. Batch Multiple Conversations
The processor supports batching multiple conversations for efficiency.

## Implementation Considerations

### 1. Model Loading
- Use `AudioFlamingo3ForConditionalGeneration.from_pretrained()`
- Use `AutoProcessor.from_pretrained()`
- Set `device_map="auto"` for automatic GPU placement
- Consider `torch_dtype` for memory optimization (BF16 recommended)

### 2. Input Processing
- Use `processor.apply_chat_template()` with:
  - `tokenize=True`
  - `add_generation_prompt=True`
  - `return_dict=True`
- Move inputs to model device: `.to(model.device)`

### 3. Generation Parameters
- `max_new_tokens`: Up to 2048 (default examples use 256-1024)
- `do_sample`: Boolean for sampling vs greedy
- `temperature`: 0.7 (example)
- `top_p`: 0.9 (example)

### 4. Output Decoding
- Decode only new tokens: `outputs[:, inputs.input_ids.shape[1]:]`
- Use `processor.batch_decode()` with `skip_special_tokens=True`

### 5. Performance Optimizations

#### Flash Attention 2 (if GPU supports it)
```python
model = AudioFlamingo3ForConditionalGeneration.from_pretrained(
    model_id,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    attn_implementation="flash_attention_2"
)
```

#### Torch Compile (not compatible with Flash Attention 2)
```python
import torch
torch.set_float32_matmul_precision("high")
model.generation_config.cache_implementation = "static"
model.forward = torch.compile(model.forward, mode="reduce-overhead", fullgraph=True)
```

#### PyTorch SDPA (fallback)
```python
model = AudioFlamingo3ForConditionalGeneration.from_pretrained(
    model_id,
    attn_implementation="sdpa"
)
```

## Prompt Engineering Considerations

### No System Prompt Needed
The model uses a conversation format with `role: "user"` and `role: "assistant"`. The processor's `apply_chat_template()` handles the formatting automatically.

### Effective Prompt Patterns (from examples)

1. **Detailed Analysis Request**:
   ```
   "Describe this track in full detail - tell me the genre, tempo, and key,
   then dive into the instruments, production style, and overall mood it creates."
   ```

2. **Rich Caption Request**:
   ```
   "Write a rich caption that blends the technical details (genre, BPM, key,
   chords, mix) with how the song feels emotionally and dynamically as it unfolds."
   ```

3. **Specific Questions**:
   ```
   "What's the key of this song?"
   "What's the bpm of this song?"
   ```

### For Our Use Case (Music Teaching)

We should design prompts that:
- Ask for pedagogical insights (what to practice, what's good/bad)
- Request structured analysis (technique, timing, pitch, expression)
- Encourage actionable feedback
- Compare performances (if we have reference audio)

Example prompts:
- "Analyze this piano performance. What are the main technical issues? What should the student focus on practicing?"
- "Compare this performance to the reference. What are the key differences in tempo, dynamics, and articulation?"
- "Provide detailed feedback on the rhythm accuracy, pitch intonation, and musical expression in this recording."

## Audio Preprocessing

Since the model processes audio in 30-second windows with a 10-minute cap:
1. **Truncation**: If audio > 10 minutes, we need to decide:
   - Truncate to first 10 minutes?
   - Process in chunks and aggregate?
   - Use a sliding window approach?

2. **Format Conversion**: Ensure audio is in supported format (WAV/MP3/FLAC)
   - Our existing `AudioPreprocessingService` can handle this
   - Should convert to WAV at 16kHz (or model's expected sample rate)

3. **Sample Rate**: Check what sample rate the model expects (likely 16kHz based on config)

## Error Handling

- Handle cases where audio file doesn't exist
- Handle audio files that are too long (> 20 minutes)
- Handle invalid audio formats
- Handle model loading failures
- Handle GPU out-of-memory errors

## Integration with Main Zikos Service

The service should:
1. Accept audio file IDs (from main service's audio storage)
2. Accept text prompts (from LLM or directly from user)
3. Return structured analysis that can be:
   - Used by the main LLM for further processing
   - Displayed directly to the user
   - Stored for later reference

## Testing Strategy

1. **Unit Tests**:
   - Mock model and processor
   - Test conversation format construction
   - Test audio path handling
   - Test error cases

2. **Integration Tests**:
   - Test with small audio samples
   - Test text-only prompts
   - Test audio-only prompts
   - Test batch processing

3. **Performance Tests**:
   - Measure inference time
   - Monitor memory usage
   - Test with various audio lengths

## Dependencies

Required packages (already in pyproject.toml):
- `transformers>=4.35.0` (need latest from git for Music Flamingo support)
- `accelerate>=0.24.0`
- `torch>=2.0.0`
- `torchaudio>=2.0.0`

Optional for optimization:
- `flash-attn` (for Flash Attention 2)

## Next Steps

1. Implement `MusicFlamingoService.initialize()` to load model and processor
2. Implement audio preprocessing/validation
3. Implement `MusicFlamingoService.infer()` with proper conversation format
4. Add error handling and logging
5. Connect to FastAPI endpoint
6. Add tests following TDD approach

---

# LLM Service Refactoring

## Overview

The `LLMService` class in `backend/zikos/services/llm.py` was a 1300+ line "god object" with multiple responsibilities mixed together. This refactoring extracts focused, testable components while maintaining backward compatibility.

## Problems Identified

1. **Massive code duplication**: `generate_response` and `generate_response_stream` shared ~70% of logic
2. **God object anti-pattern**: Single class handling 10+ responsibilities
3. **Hard to test**: Tight coupling, many side effects, hard to mock
4. **Inconsistent patterns**: Mixed error handling, magic numbers, print statements everywhere
5. **Poor separation of concerns**: Audio analysis, tool injection, validation, execution all mixed

## Refactoring Strategy

Extract focused classes with single responsibilities:

1. ✅ **ThinkingExtractor** - Extracts thinking from `<thinking>` tags
2. ✅ **ConversationManager** - Manages conversation history per session
3. ✅ **MessagePreparer** - Prepares messages, handles truncation, system prompt injection
4. ⏳ **AudioContextEnricher** - Enriches messages with audio analysis context
5. ⏳ **ToolInjector** - Injects tools into system prompts
6. ⏳ **ToolCallParser** - Parses native and Qwen XML tool calls
7. ⏳ **ToolExecutor** - Executes tools, handles errors, widget detection
8. ⏳ **ResponseValidator** - Validates responses (gibberish, tokens, loops)
9. ⏳ **LLMOrchestrator** - Orchestrates generate_response and generate_response_stream

## Progress

### Completed (2024-12-XX)

- ✅ Extracted `ThinkingExtractor` class
- ✅ Extracted `ConversationManager` class
- ✅ Extracted `MessagePreparer` class
- ✅ Added missing constants for tool calling limits
- ✅ Fixed type annotations for mypy compliance
- ✅ All existing tests pass (backward compatibility maintained)

### In Progress

- ⏳ Extracting remaining orchestration components
- ⏳ Replacing print() statements with proper logging
- ⏳ Creating comprehensive test suite

## Design Principles

1. **Single Responsibility**: Each class has one clear purpose
2. **Testability**: Components can be tested in isolation
3. **Reusability**: Shared logic extracted to avoid duplication
4. **Backward Compatibility**: Public API unchanged, internal refactoring only
5. **TDD Approach**: Tests written/verified at each step

## File Structure

```
backend/zikos/services/
├── llm.py (main service, thin facade)
└── llm_orchestration/
    ├── __init__.py
    ├── thinking_extractor.py ✅
    ├── conversation_manager.py ✅
    ├── message_preparer.py ✅
    ├── audio_context_enricher.py ✅
    ├── tool_injector.py ✅
    ├── tool_call_parser.py ✅
    ├── tool_executor.py ✅
    ├── response_validator.py ✅
    └── orchestrator.py ✅
```

## Constants Added

Added to `backend/zikos/constants.py`:
- `MAX_CONSECUTIVE_TOOL_CALLS = 5`
- `RECENT_TOOL_CALLS_WINDOW = 10`
- `REPETITIVE_PATTERN_THRESHOLD = 4`

## Completed Extractions

### 1. ThinkingExtractor ✅
- Extracts thinking content from `<thinking>` tags
- Returns cleaned content and thinking separately

### 2. ConversationManager ✅
- Manages conversation history per session
- Handles system prompt injection
- Provides thinking retrieval for debugging

### 3. MessagePreparer ✅
- Prepares and truncates messages for LLM
- Handles system prompt inclusion
- Manages audio analysis message prioritization

### 4. AudioContextEnricher ✅
- Enriches user messages with audio analysis context
- Finds recent audio analysis in history
- Formats context appropriately

### 5. ToolInjector ✅
- Injects tools into system prompts
- Checks for duplicate tool definitions
- Handles both system message update and creation

### 6. ToolCallParser ✅
- Parses native tool calls from LLM responses
- Parses Qwen XML-based tool calls
- Fixes common JSON issues in tool call arguments
- Strips tool call tags from content

### 7. ResponseValidator ✅
- Validates token limits
- Detects gibberish patterns (repetition, single chars, excessive length)
- Detects tool call loops (consecutive and repetitive patterns)

### 8. ToolExecutor ✅
- Executes tools via MCP server
- Handles widget detection and early returns
- Handles error cases (FileNotFoundError, general exceptions)
- Enhances error messages for MIDI tools
- Used by both generate_response and generate_response_stream

### 9. LLMOrchestrator ✅
- Orchestrates common LLM response generation logic
- Handles conversation preparation (history, audio context, tool injection)
- Manages iteration state (counters, recent tool calls)
- Processes LLM responses (thinking extraction, validation)
- Processes tool calls with loop detection
- Finalizes responses
- Used by generate_response (streaming version still has some duplication due to yield semantics)

## Testing Strategy

- Run existing tests after each extraction to ensure no regressions
- All unit tests pass
- Integration tests pass
- Coverage maintained
- Pre-commit hooks pass (black, ruff, mypy)

## Next Steps

1. Final test run to ensure everything works
2. Consider further reducing duplication in generate_response_stream (though streaming semantics make this challenging)

## Completed: Logging Migration ✅

- Replaced all `print()` statements with proper `logging.getLogger()` calls
- Added loggers to:
  - `llm.py` - Main LLM service logger
  - `response_validator.py` - Response validation logger
  - `tool_call_parser.py` - Tool call parsing logger
  - `tool_executor.py` - Tool execution logger
- Used appropriate log levels:
  - `logger.debug()` for debug information (when `settings.debug_tool_calls` is True)
  - `logger.info()` for informational messages
  - `logger.warning()` for warnings
  - `logger.error()` for errors (with `exc_info=True` for exceptions)
