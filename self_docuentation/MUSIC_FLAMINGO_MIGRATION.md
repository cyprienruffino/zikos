# Music Flamingo Migration Analysis

## Current Architecture Summary

- **Text-only LLM** (Qwen2.5/Qwen3) for chat interactions
- **Audio analysis** via librosa-based signal processing tools (tempo, pitch, rhythm, etc.)
- **Tool-based approach**: LLM receives analysis results as text/JSON
- **MCP tools** for audio processing and MIDI generation

## Required Changes

### 1. Backend Architecture Changes

**A. New Backend Implementation**
- Create a new `MusicFlamingoBackend` class (or extend `TransformersBackend`)
- Use `AudioFlamingo3ForConditionalGeneration` instead of `AutoModelForCausalLM`
- Use `AutoProcessor` instead of `AutoTokenizer`
- Handle multimodal inputs (text + audio)

**B. Input Format Changes**
- Current: text-only messages
- Required: conversation format with audio paths:
```python
conversation = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "Analyze this performance"},
        {"type": "audio", "path": "/path/to/audio.wav"}
    ]
}]
```

**C. Audio Handling**
- Preprocess audio to model requirements (format, sample rate, duration)
- Handle audio file paths vs. in-memory audio
- Support up to 20 minutes of audio
- Integrate with existing `AudioService` storage

### 2. Integration Points

**A. LLM Service (`backend/zikos/services/llm.py`)**
- Modify `generate_response()` to handle audio inputs
- Update `_prepare_messages()` for multimodal format
- Adjust conversation history handling
- Tool calling may need changes (verify if Music Flamingo supports it)

**B. Audio Service Integration**
- When audio is uploaded/recorded, pass it directly to the model
- Decision needed: direct audio input vs. keep librosa analysis as fallback
- Handle audio file IDs → file paths conversion

**C. Tool Calling**
- Verify if Music Flamingo supports function calling
- If not, keep tool-based approach but adapt the flow
- May need to parse tool calls from text output

### 3. Configuration Changes

**A. Environment Variables**
- Update `docker-compose.yml`:
  - Change `LLM_MODEL_PATH` to `nvidia/music-flamingo-hf`
  - Add audio-specific configs (max duration, sample rate)
  - Update GPU memory requirements

**B. Model Loading**
- Update `create_backend()` in `llm_backends/__init__.py`
- Detect Music Flamingo model path/name
- Handle model download from HuggingFace

### 4. Dependencies

**A. New Requirements**
- Already have `transformers` and `torch`
- May need `accelerate` for model loading
- Verify audio processing libraries compatibility

**B. Hardware Requirements**
- Music Flamingo requires NVIDIA GPU (A100/H100 recommended)
- Higher VRAM requirements than current Qwen models
- Update documentation and configuration

## Potential Improvements

### 1. Direct Audio Understanding
- Model processes audio directly instead of librosa-derived features
- Better musical understanding (genre, emotion, production style)
- Can analyze full tracks (up to 20 minutes)

### 2. Unified Model
- Single model for chat and audio analysis
- Reduces complexity vs. separate LLM + analysis tools
- More coherent responses

### 3. Enhanced Musical Reasoning
- Chain-of-thought reasoning
- Better interpretation of musical context
- More nuanced feedback

### 4. Reduced Tool Dependency
- Less reliance on librosa analysis tools
- Simpler architecture (fewer moving parts)
- Faster feedback (no separate analysis step)

## Potential Issues & Concerns

### 1. Tool Calling Support ⚠️ CRITICAL
- **Critical**: Music Flamingo may not support function calling
- Current architecture relies heavily on MCP tools
- If unsupported, options:
  - Parse tool calls from text (fragile)
  - **Hybrid approach**: Use Music Flamingo for audio understanding, keep Qwen for tool orchestration
  - Redesign to reduce tool dependency

### 2. Output Limitations
- Max 2,048 tokens output (vs. current flexible length)
- May truncate detailed feedback
- Need truncation/streaming strategy

### 3. Context Window
- Max 24,000 tokens input
- Current system uses 32K+ context
- May need to truncate conversation history more aggressively

### 4. Audio Preprocessing
- Model expects specific audio format/sample rate
- Need preprocessing pipeline
- Handle various input formats (WAV, MP3, FLAC)

### 5. Performance & Resource Requirements
- Higher VRAM than current models
- Slower inference (multimodal processing)
- May need model quantization or optimization

### 6. Integration Complexity
- Current flow: Audio → librosa analysis → text → LLM
- New flow: Audio → Music Flamingo (direct)
- Significant refactoring of `handle_audio_ready()` and related code

### 7. Backward Compatibility
- Existing tests may break
- Tool-based analysis may still be needed for some features
- Consider keeping both paths (hybrid approach)

### 8. Model Availability & Licensing
- Verify HuggingFace model availability
- Check licensing for commercial use
- Model size and download requirements

## Design Questions to Consider

1. **Tool Calling**: Does Music Flamingo support function calling? If not, how do we handle MCP tools?
2. **Hybrid Approach**: Use Music Flamingo for audio understanding + Qwen for tool orchestration?
3. **Analysis Tools**: Keep librosa tools as fallback/validation, or fully replace?
4. **MIDI Generation**: Can Music Flamingo generate MIDI, or keep current text-based approach?
5. **Conversation Flow**: How to handle multi-turn conversations with audio context?

## Recommended Approach

### Phase 1: Proof of Concept
- Create `MusicFlamingoBackend` class
- Test basic audio + text inference
- Verify tool calling support

### Phase 2: Integration
- Integrate with existing audio upload flow
- Update `handle_audio_ready()` to use Music Flamingo
- Keep librosa tools as fallback

### Phase 3: Optimization
- Handle tool calling (or hybrid approach)
- Optimize performance and memory
- Update tests and documentation

## User Feedback & Decisions

### Hybrid Approach (Preferred)
- **Qwen orchestrates tools** and handles analysis
- **Music Flamingo as sophisticated tool** - can be called when needed
- **Remote service option** - Music Flamingo can run on dedicated service
- **Benefits**:
  - Keeps existing architecture mostly intact
  - Leverages both signal processing (exact) and model predictions (semantic)
  - Easier incremental rollout
  - Better resource management

### Streaming Strategies
- **Context window extension**: Need to explore sliding window, summarization, or retrieval-augmented generation
- **Output streaming**: Stream tokens as they're generated to handle 2,048 token limit

### Audio Preprocessing
- **FFmpeg integration**: Implement audio transcoding as preprocessing step
- **Add ffmpeg as dependency**: Handle various input formats (WAV, MP3, FLAC)
- **Standardize format**: Convert to model-required format/sample rate

### Librosa Tools Retention
- **Keep signal processing tools**: Provide exact measurements vs. model predictions
- **Complementary information**: Both approaches valuable
- **Hybrid analysis**: Combine librosa precision with Music Flamingo semantic understanding

### Implementation Strategy
- **Option 1**: Add Music Flamingo as optional tool (recommended for incremental rollout)
- **Option 2**: Replace model completely (simpler but loses tool calling)
- **Decision**: Prefer Option 1 - keeps current workflow, adds capability
