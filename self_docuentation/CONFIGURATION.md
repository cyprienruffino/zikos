# Configuration Reference

## Environment Variables

### LLM Configuration
- `LLM_MODEL_PATH`: Path to model file/directory (required)
- `LLM_BACKEND`: `auto` | `llama_cpp` | `transformers` (default: `auto`)
- `LLM_N_CTX`: Context window size (optional, auto-detected from model if not set)
- `LLM_N_GPU_LAYERS`: GPU layers (-1=auto/full, 0=CPU only, N=partial) (default: -1)
- `LLM_TEMPERATURE`: Sampling temperature 0.0-1.0 (default: 0.7)
- `LLM_TOP_P`: Top-p sampling 0.0-1.0 (default: 0.9)

### API Configuration
- `API_HOST`: Bind address (default: `0.0.0.0`)
- `API_PORT`: Port number (default: 8000)
- `API_RELOAD`: Auto-reload on changes (default: `false`)

### Storage Paths
- `AUDIO_STORAGE_PATH`: Audio storage directory (default: `audio_storage`)
- `MIDI_STORAGE_PATH`: MIDI storage directory (default: `midi_storage`)
- `NOTATION_STORAGE_PATH`: Notation storage directory (default: `notation_storage`)

### Debug
- `DEBUG_TOOL_CALLS`: Verbose tool calling logs (default: `false`)

## Model Selection by Hardware

### CPU-Only
- Model: TinyLlama 1.1B Chat Q4_K_M (~670MB RAM) - **RECOMMENDED**
- Config: `LLM_N_GPU_LAYERS=0`, `LLM_N_CTX=2048`
- Performance: Fast on CPU, limited function calling
- Alternative: Mistral 7B Instruct Q4_K_M (~4.5GB RAM, slower but better quality)

### 8GB VRAM (RTX 3060Ti, 3070, 4060Ti)
- Model: Mistral 7B Instruct v0.3 Q4_K_M (~4.5GB VRAM) - **RECOMMENDED**
- Config: `LLM_N_GPU_LAYERS=-1`, `LLM_N_CTX=8192`
- Alternative: Qwen2.5-7B-Instruct Q4_K_M (~4.5GB VRAM, better function calling)

### 16-24GB VRAM (RTX 3090, 4090, A4000)
- Model: Mistral 7B Instruct v0.3 Q5_K_M (~5.5GB VRAM) or Qwen2.5-14B-Instruct Q4_K_M (~8GB VRAM)
- Config: `LLM_N_GPU_LAYERS=-1`, `LLM_N_CTX=8192-32768`
- Alternative: Llama 3.3 70B Q4_K_M (~40GB VRAM)

### 80GB+ VRAM (H100, A100)
- Model: Qwen3-32B-Instruct (~65GB VRAM)
- Backend: `transformers` (not `llama_cpp`)
- Config: `LLM_BACKEND=transformers`, `LLM_N_CTX=131072`, `LLM_N_GPU_LAYERS=-1`
- Alternative: Qwen3-30B-A3B MoE (~40GB VRAM, faster inference)
- Alternative: Llama 3.3 70B Q5_K_M (~50GB VRAM)

## Model Context Windows

| Model | Native Context | Extended Context | Backend |
|-------|---------------|------------------|---------|
| TinyLlama 1.1B | 2K | 2K (native) | llama_cpp |
| Mistral 7B | 8K | 8K (native) | llama_cpp |
| Qwen2.5-7B | 32K | 32K (native) | llama_cpp |
| Qwen2.5-14B | 32K | 32K (native) | llama_cpp |
| Qwen3-32B | 128K | 128K (native) | transformers |
| Qwen3-14B | 128K | 128K (native) | transformers |
| Qwen3-8B | 32K | 128K (with RoPE) | transformers |
| Llama 3.3 70B | 8K | 128K+ (with RoPE) | llama_cpp |

## Backend Detection

- `auto`: Detects based on model path
  - `.gguf` file → `llama_cpp`
  - Directory → `transformers`
- `llama_cpp`: GGUF models (TinyLlama, Mistral, Qwen2.5, Llama)
- `transformers`: HuggingFace models (Qwen3)

## GPU Configuration

### Auto-Detection
- GPU detected via PyTorch or nvidia-smi
- `LLM_N_GPU_LAYERS=-1` → full GPU offload
- Transformers: uses `device_map="auto"`

### Manual Override
- `LLM_N_GPU_LAYERS=0`: Force CPU
- `LLM_N_GPU_LAYERS=N`: Partial GPU offload (N layers on GPU)
- `LLM_N_GPU_LAYERS=-1`: Full GPU offload (recommended)

## Performance Optimization

### Transformers Backend
- Flash Attention 2: auto-enabled if available
- BFloat16: default dtype for GPU
- Device map: auto-distributes across GPUs

### LlamaCpp Backend
- GPU layers: `-1` for full offload
- Context: handles large contexts efficiently
- Quantization: Q5_K_M recommended for quality/speed

## Troubleshooting

### Out of Memory
1. Reduce `LLM_N_CTX` (e.g., 65536 instead of 131072)
2. Use lower quantization (Q4 instead of Q5)
3. Use MoE models (Qwen3-30B-A3B uses less VRAM)
4. Partial GPU offload: `LLM_N_GPU_LAYERS=30`

### Model Not Found
- GGUF: Path must point to `.gguf` file
- Transformers: Path must point to model directory (not file)
- Use absolute path or relative to project root

### Slow Inference
- Check GPU usage: `nvidia-smi`
- Ensure `LLM_N_GPU_LAYERS=-1` for full GPU offload
- Consider MoE models for faster inference

### Backend Detection Issues
- Set explicit backend: `LLM_BACKEND=llama_cpp` or `LLM_BACKEND=transformers`
- Check model format: GGUF files → llama_cpp, HuggingFace dirs → transformers

## Remote Execution

- API host already set to `0.0.0.0` (works for remote access)
- SSH tunnel: `ssh -L 8000:localhost:8000 user@remote-server`
- Access: `http://localhost:8000` from local machine
- No hardcoded localhost dependencies
