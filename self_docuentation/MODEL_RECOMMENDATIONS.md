# Model Recommendations

## Quick Decision Guide

**By GPU VRAM:**
- **8GB VRAM or less** → Qwen2.5-7B-Instruct
- **16GB VRAM** → Qwen2.5-14B-Instruct
- **80GB VRAM (H100)** → Qwen3-32B-Instruct

**No GPU?** → Qwen2.5-7B-Instruct (runs on CPU, slower)

## Recommended Models

### ⭐ Qwen2.5-7B-Instruct (Best for Most Users)
- **Best for**: Standard GPUs (8GB VRAM), CPU-only setups
- **Size**: ~4.5GB
- **Performance**: Excellent function calling, fast responses
- **Context**: 32K tokens
- **Why**: Best balance of quality, speed, and resource usage

### Qwen2.5-14B-Instruct (If You Have More VRAM)
- **Best for**: GPUs with 16GB+ VRAM
- **Size**: ~8GB
- **Performance**: Better quality than 7B, slightly slower
- **Context**: 32K tokens
- **Why**: Better responses if you have the resources

### Qwen3-32B-Instruct (High-End GPUs Only)
- **Best for**: H100 or similar high-VRAM GPUs (80GB+)
- **Size**: ~65GB VRAM
- **Performance**: Best quality, largest context window
- **Context**: 128K tokens
- **Why**: Maximum quality and context capacity

## Alternative Models

### Mistral-7B-Instruct-v0.3
- **Best for**: If Qwen models aren't available
- **Size**: ~4.5GB
- **Performance**: Good function calling, reliable
- **Context**: 8K tokens (smaller than Qwen)
- **Note**: Smaller context window than Qwen models

### Llama 3.2-8B-Instruct
- **Best for**: If you prefer Llama models
- **Size**: ~4.5GB
- **Performance**: Good, but not as good as Qwen for function calling
- **Context**: 8K tokens
- **Note**: Qwen models are generally better for this use case

## Model Comparison

| Model | Quality | Size | Context | Speed | Best For |
|-------|---------|------|---------|-------|----------|
| Qwen2.5-7B | ⭐⭐⭐⭐⭐ | 4.5GB | 32K | Fast | **Most users** |
| Qwen2.5-14B | ⭐⭐⭐⭐⭐ | 8GB | 32K | Medium | More VRAM available |
| Qwen3-32B | ⭐⭐⭐⭐⭐ | 65GB | 128K | Medium | H100 GPUs or better |
| Mistral-7B | ⭐⭐⭐⭐ | 4.5GB | 8K | Fast | Alternative option |
| Llama 3.2-8B | ⭐⭐⭐ | 4.5GB | 8K | Fast | Llama preference |

## Why Qwen Models?

Qwen models are specifically optimized for function calling and tool use:
1. **Better function calling**: More reliable at using tools correctly
2. **Larger context**: 32K tokens vs 8K for most alternatives
3. **Better instruction following**: Handles complex requests more accurately
