# LLM Model Recommendations for Function Calling

## Current Situation

The current Llama 3.1/3.2 8B models are experiencing issues with function calling:
- Models generate garbage text instead of calling tools
- Keyword-based fallback detection is unreliable
- Function calling support is limited in smaller Llama models

## Recommended Models (Best to Good)

### ⭐ **Qwen2.5-7B-Instruct** (HIGHLY RECOMMENDED)
- **Function Calling**: Excellent - specifically trained for tool use
- **Size**: ~4.5GB (Q4_K_M), ~5.5GB (Q5_K_M)
- **Performance**: Best function calling among 7B models
- **Context**: 32K tokens
- **Why**: Qwen models are specifically optimized for function calling and tool use, making them ideal for this use case

**Download**: `python scripts/download_model.py qwen2.5-7b-instruct-q4`

### **Qwen2.5-14B-Instruct** (If you have more RAM)
- **Function Calling**: Excellent
- **Size**: ~8GB (Q4_K_M)
- **Performance**: Even better than 7B, but requires more resources
- **Context**: 32K tokens

**Download**: `python scripts/download_model.py qwen2.5-14b-instruct-q4`

### **Mistral-7B-Instruct-v0.3** (Good Alternative)
- **Function Calling**: Good - better than Llama 3.1/3.2
- **Size**: ~4.5GB (Q4_K_M)
- **Performance**: Reliable function calling, well-tested
- **Context**: 8K tokens (smaller than Qwen)

**Download**: `python scripts/download_model.py mistral-7b-instruct-v0.3-q4`

### **Llama 3.2-8B-Instruct** (Better than 3.1)
- **Function Calling**: Good - improved over 3.1
- **Size**: ~4.5GB (Q4_K_M)
- **Performance**: Better function calling than 3.1, but still not as good as Qwen
- **Context**: 8K tokens

**Download**: `python scripts/download_model.py llama-3.2-8b-instruct-q4`

## Model Comparison

| Model | Function Calling | Size (Q4) | Context | Speed | Recommendation |
|-------|-----------------|-----------|---------|-------|----------------|
| Qwen2.5-7B | ⭐⭐⭐⭐⭐ | 4.5GB | 32K | Fast | **Best choice** |
| Qwen2.5-14B | ⭐⭐⭐⭐⭐ | 8GB | 32K | Medium | If you have RAM |
| Mistral-7B v0.3 | ⭐⭐⭐⭐ | 4.5GB | 8K | Fast | Good alternative |
| Llama 3.2-8B | ⭐⭐⭐ | 4.5GB | 8K | Fast | Better than 3.1 |
| Llama 3.1-8B | ⭐⭐ | 4.5GB | 8K | Fast | Not recommended |

## Why Qwen2.5 is Recommended

1. **Purpose-built for function calling**: Qwen models are specifically trained and optimized for tool use
2. **Larger context window**: 32K tokens vs 8K for Llama/Mistral
3. **Better instruction following**: More reliable at following complex tool-calling instructions
4. **Proven track record**: Widely used in agent applications

## Migration Steps

1. **Download recommended model**:
   ```bash
   python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models
   ```

2. **Update environment variable**:
   ```bash
   export LLM_MODEL_PATH=./models/qwen2.5-7b-instruct-q4_k_m.gguf
   ```
   Or in `.env`:
   ```
   LLM_MODEL_PATH=./models/qwen2.5-7b-instruct-q4_k_m.gguf
   ```

3. **Test function calling**: The code changes (removing keyword spotting) will rely entirely on the model's native function calling capabilities.

## Notes

- All models listed are available in GGUF format compatible with llama-cpp-python
- Q4_K_M quantization provides good balance of quality and size
- Q5_K_M provides better quality but larger file size
- For production, Qwen2.5-7B Q4_K_M is the sweet spot

## Resources

- Qwen models: https://huggingface.co/Qwen
- Mistral models: https://huggingface.co/mistralai
- Llama models: https://huggingface.co/meta-llama
