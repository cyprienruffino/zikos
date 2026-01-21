# Model Recommendations

## Quick Decision Guide

**By GPU VRAM:**
- **No GPU / CPU-only** → TinyLlama 1.1B (recommended)
- **8GB VRAM or less** → Mistral 7B Instruct
- **16GB+ VRAM** → Mistral 7B Instruct or larger models

## Recommended Models

### ⭐ TinyLlama 1.1B Chat (Best for CPU-Only)
- **Best for**: CPU-only setups, low-resource environments
- **Size**: ~670MB
- **Performance**: Limited function calling, very fast on CPU
- **Context**: 2K tokens
- **Why**: Smallest model, runs well on CPU without GPU

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
| TinyLlama 1.1B | ⭐⭐⭐ | 670MB | 2K | Very Fast | **CPU-only** |
| Mistral 7B | ⭐⭐⭐⭐ | 4.5GB | 8K | Fast | **GPU users** |
| Qwen2.5-7B | ⭐⭐⭐⭐⭐ | 4.5GB | 32K | Fast | Better function calling |
| Qwen2.5-14B | ⭐⭐⭐⭐⭐ | 8GB | 32K | Medium | More VRAM available |
| Qwen3-32B | ⭐⭐⭐⭐⭐ | 65GB | 128K | Medium | H100 GPUs or better |
| Llama 3.2-8B | ⭐⭐⭐ | 4.5GB | 8K | Fast | Llama preference |
