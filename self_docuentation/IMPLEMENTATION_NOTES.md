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
