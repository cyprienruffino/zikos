# Model Recommendations

## Quick Decision Guide

**By GPU VRAM:**
- **No GPU / CPU-only** → Phi-3 Mini 4K (recommended) or Llama 3.2 8B if you have enough RAM
- **8GB VRAM or less** → Mistral 7B Instruct
- **16GB+ VRAM** → Mistral 7B Instruct or larger models

## Recommended Models

### ⭐ Phi-3 Mini 4K Instruct (Best for CPU-Only)
- **Best for**: CPU-only setups, low-resource environments
- **Size**: ~2.3GB
- **Performance**: Moderate function calling, better instruction following than TinyLlama
- **Context**: 4K tokens
- **Why**: Small enough for CPU, but handles system messages and instructions much better than TinyLlama
- **Note**: TinyLlama is no longer recommended due to poor instruction following

### ⭐ Mistral 7B Instruct v0.3 (Best for GPU)
- **Best for**: GPUs with 8GB+ VRAM
- **Size**: ~4.5GB
- **Performance**: Good function calling, reliable
- **Context**: 8K tokens
- **Why**: Best balance of quality, speed, and resource usage for GPU setups

## Alternative Models

### Qwen2.5-7B-Instruct
- **Best for**: If you need better function calling than Mistral
- **Size**: ~4.5GB
- **Performance**: Excellent function calling, fast responses
- **Context**: 32K tokens
- **Note**: Larger context window than Mistral

### Qwen2.5-14B-Instruct
- **Best for**: GPUs with 16GB+ VRAM
- **Size**: ~8GB
- **Performance**: Better quality than 7B, slightly slower
- **Context**: 32K tokens
- **Note**: Better responses if you have the resources

### Qwen3-32B-Instruct (High-End GPUs Only)
- **Best for**: H100 or similar high-VRAM GPUs (80GB+)
- **Size**: ~65GB VRAM
- **Performance**: Best quality, largest context window
- **Context**: 128K tokens
- **Note**: Maximum quality and context capacity

### Llama 3.2-8B-Instruct
- **Best for**: If you prefer Llama models
- **Size**: ~4.5GB
- **Performance**: Good function calling
- **Context**: 8K tokens

## Model Comparison

| Model | Quality | Size | Context | Speed | Best For |
|-------|---------|------|---------|-------|----------|
| Phi-3 Mini 4K | ⭐⭐⭐⭐ | 2.3GB | 4K | Fast | **CPU-only** |
| Mistral 7B | ⭐⭐⭐⭐ | 4.5GB | 8K | Fast | **GPU users** |
| Qwen2.5-7B | ⭐⭐⭐⭐⭐ | 4.5GB | 32K | Fast | Better function calling |
| Qwen2.5-14B | ⭐⭐⭐⭐⭐ | 8GB | 32K | Medium | More VRAM available |
| Qwen3-32B | ⭐⭐⭐⭐⭐ | 65GB | 128K | Medium | H100 GPUs or better |
| Llama 3.2-8B | ⭐⭐⭐ | 4.5GB | 8K | Fast | Llama preference |
