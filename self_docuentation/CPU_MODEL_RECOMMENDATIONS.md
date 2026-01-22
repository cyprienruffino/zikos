# CPU-Only Model Recommendations (2025)

## Current Recommendation: Phi-3 Mini 4K Instruct

**Model**: `phi-3-mini-q4`
**Size**: ~2.3GB
**Context**: 4K tokens
**Performance**: Moderate speed on CPU, better instruction following than TinyLlama

### Why Phi-3 Mini?

- **Better instruction following**: Handles system messages and tool calling better than TinyLlama
- **Still CPU-friendly**: Small enough to run on CPU (albeit slowly)
- **4K context**: Better than TinyLlama's 2K context window
- **Microsoft quality**: Well-trained for instruction following

### Download

```bash
python scripts/download_model.py phi-3-mini-q4 -o ./models
export LLM_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
export LLM_N_GPU_LAYERS=0  # CPU only
```

## Alternative: Llama 3.2 8B Instruct (if you have enough RAM)

**Model**: `llama-3.2-8b-instruct-q4`
**Size**: ~4.5GB
**Context**: 8K tokens
**Performance**: Slower on CPU, but much better quality and function calling

### When to Use

- You have 8GB+ RAM available
- You can tolerate slower inference (still CPU-only)
- You need better function calling and instruction following

### Download

```bash
python scripts/download_model.py llama-3.2-8b-instruct-q4 -o ./models
export LLM_MODEL_PATH=./models/Llama-3.2-8B-Instruct-Q4_K_M.gguf
export LLM_N_GPU_LAYERS=0  # CPU only
```

## Why Not TinyLlama?

TinyLlama has been removed as the recommended CPU model due to:
- Poor instruction following (echoes system prompts instead of following them)
- Limited function calling capability
- Poor instruction following and system message handling
- Generates unrelated/confused responses

## Future Models to Watch (2025/2026)

As of early 2025, these models show promise but may not be available in GGUF format yet:
- **SmolLM2**: Very small, efficient models (check for GGUF conversions)
- **Gemma 2B**: Google's small model (check for GGUF conversions)
- **Qwen2.5 1.5B**: If available, might be better than TinyLlama

Check HuggingFace for GGUF conversions of these models if you want to try them.
