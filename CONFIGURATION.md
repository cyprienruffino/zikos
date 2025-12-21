# Configuration Guide

This guide helps you configure Zikos for your hardware setup.

## Quick Start

### Option 1: Automated Setup (Recommended)

Use the setup script for your platform:

**Linux/Mac**:
```bash
# For RTX 3060Ti / 8GB VRAM
./scripts/setup_env.sh small

# For RTX 4090 / 24GB VRAM
./scripts/setup_env.sh medium

# For H100 / 80GB VRAM
./scripts/setup_env.sh large

# For CPU-only (no GPU)
./scripts/setup_env.sh cpu
```

**Windows PowerShell**:
```powershell
# For RTX 3060Ti / 8GB VRAM
.\scripts\setup_env.ps1 small

# For RTX 4090 / 24GB VRAM
.\scripts\setup_env.ps1 medium

# For H100 / 80GB VRAM
.\scripts\setup_env.ps1 large

# For CPU-only (no GPU)
.\scripts\setup_env.ps1 cpu
```

### Option 2: Manual Setup

1. **Create `.env` file** with the appropriate configuration (see examples below)
2. **Download a model** (see model recommendations below)
3. **Update `LLM_MODEL_PATH`** in `.env` with your model path
4. **Run the application**: `python run.py`

## Hardware Profiles

### CPU-Only Setup (No GPU)

**Hardware**: Any CPU (Intel, AMD, Apple Silicon), no GPU required

**Configuration**: Use `cpu` profile

**Recommended Models**:
- Qwen2.5-7B-Instruct Q4_K_M (~4.5GB RAM)
- Smaller models work better for CPU-only

**Settings**:
- Context window: 16K tokens (reduced for CPU performance)
- GPU layers: 0 (CPU only)
- Backend: llama_cpp (GGUF)

**Download model**:
```bash
python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models
```

**Update `.env`**:
```bash
LLM_MODEL_PATH=./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_N_CTX=16384
LLM_N_GPU_LAYERS=0
```

**Performance Notes**:
- CPU inference is slower than GPU (expect 2-10x slower)
- Use smaller context windows for better performance
- Consider using smaller models (7B or less)
- Multi-threading helps but won't match GPU speed

### Small GPU Setup (8GB VRAM)

**Hardware**: RTX 3060Ti, RTX 3070, RTX 4060Ti, similar GPUs

**Configuration**: `.env.example.small`

**Recommended Models**:
- Qwen2.5-7B-Instruct Q4_K_M (~4.5GB VRAM)
- Qwen2.5-14B-Instruct Q4_K_M (~8GB VRAM, tight fit)

**Settings**:
- Context window: 32K tokens
- GPU layers: Auto-detected (typically 35 for 7B models)
- Backend: llama_cpp (GGUF)

**Download model**:
```bash
python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models
```

**Update `.env`**:
```bash
LLM_MODEL_PATH=./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_N_CTX=32768
LLM_N_GPU_LAYERS=-1
```

### Medium GPU Setup (16-24GB VRAM)

**Hardware**: RTX 3090, RTX 4090, A4000, similar GPUs

**Configuration**: `.env.example.medium`

**Recommended Models**:
- Qwen2.5-14B-Instruct Q4_K_M (~8GB VRAM)
- Qwen2.5-14B-Instruct Q5_K_M (~10GB VRAM, better quality)
- Llama 3.3 70B Q4_K_M (~40GB VRAM, requires 16GB+)

**Settings**:
- Context window: 32K-64K tokens
- GPU layers: Auto-detected (full GPU offload)
- Backend: llama_cpp (GGUF)

**Download model**:
```bash
python scripts/download_model.py qwen2.5-14b-instruct-q5 -o ./models
```

**Update `.env`**:
```bash
LLM_MODEL_PATH=./models/Qwen2.5-14B-Instruct-Q5_K_M.gguf
LLM_N_CTX=32768
LLM_N_GPU_LAYERS=-1
```

### Large GPU Setup (80GB+ VRAM)

**Hardware**: H100, A100 (80GB), similar high-end GPUs

**Configuration**: `.env.example.large`

With an H100 GPU, you can run much larger models with larger context windows than typical setups.

#### Recommended Models

**⭐ Qwen3-32B-Instruct** (RECOMMENDED):
- **Parameters**: 32.8B
- **Context Window**: 128K tokens (native)
- **VRAM Required**: ~65GB (fits comfortably in 80GB)
- **Function Calling**: Excellent
- **Backend**: Transformers (HuggingFace)
- **Why**: Best balance of quality, context window, and VRAM usage

**Qwen3-30B-A3B MoE**:
- **Parameters**: 30.5B total, ~3.3B active
- **Context Window**: 128K tokens
- **VRAM Required**: ~40GB
- **Function Calling**: Excellent
- **Backend**: Transformers
- **Why**: MoE architecture means faster inference with similar quality

**Llama 3.3 70B-Instruct**:
- **Parameters**: 70B
- **Context Window**: 8K native, extendable to 128K+ with RoPE
- **VRAM Required**: ~40GB (Q4), ~50GB (Q5)
- **Function Calling**: Excellent
- **Backend**: llama-cpp-python (GGUF)

#### Setup

**Download model**:
```bash
# Qwen3-32B (recommended)
python scripts/download_model.py qwen3-32b-instruct -o ./models

# Or Qwen3-30B-A3B MoE (faster)
python scripts/download_model.py qwen3-30b-a3b-moe -o ./models

# Or Llama 3.3 70B
python scripts/download_model.py llama-3.3-70b-instruct-q5 -o ./models
```

**Update `.env`** (Qwen3-32B example):
```bash
LLM_MODEL_PATH=./models/Qwen_Qwen3-32B-Instruct
LLM_BACKEND=transformers
LLM_N_CTX=131072
LLM_N_GPU_LAYERS=-1
```

**Update `.env`** (Llama 3.3 70B example):
```bash
LLM_MODEL_PATH=./models/Llama-3.3-70B-Instruct-Q5_K_M.gguf
LLM_BACKEND=llama_cpp
LLM_N_CTX=131072
LLM_N_GPU_LAYERS=-1
```

#### GPU Configuration

**Auto-Detection**: The system automatically detects GPU and configures optimal settings:
- **GPU Detection**: Automatically detects NVIDIA GPUs via PyTorch or nvidia-smi
- **Optimal Layers**: Automatically sets `n_gpu_layers=-1` for full GPU offload on large models
- **Memory Management**: Uses `device_map="auto"` for Transformers models

**Manual Override**:
```bash
# Force CPU (for testing)
export LLM_N_GPU_LAYERS=0

# Force specific GPU layers (for llama-cpp-python)
export LLM_N_GPU_LAYERS=60

# Full GPU offload (recommended for H100)
export LLM_N_GPU_LAYERS=-1
```

#### Context Window Configuration

**Default Settings**:
- **Default Context**: 131,072 tokens (128K)
- **Maximum Supported**: Up to 512K+ tokens (model-dependent)

**Configuration**:
```bash
# 128K context (recommended for Qwen3)
export LLM_N_CTX=131072

# 256K context (if model supports it)
export LLM_N_CTX=262144

# Smaller context for faster inference
export LLM_N_CTX=65536
```

**Model-Specific Context Windows**:

| Model | Native Context | Extended Context |
|-------|---------------|------------------|
| Qwen3-32B | 128K | 128K (native) |
| Qwen3-14B | 128K | 128K (native) |
| Qwen3-8B | 32K | 128K (with RoPE) |
| Llama 3.3 70B | 8K | 128K+ (with RoPE) |

#### Performance Optimization

**Transformers Backend**:
- **Flash Attention**: Automatically used if available (faster, lower memory)
- **BFloat16**: Default dtype for GPU (better performance than FP32)
- **Device Map**: Automatically distributes model across available GPUs

**LlamaCpp Backend**:
- **GPU Layers**: Set to `-1` for full GPU offload
- **Context**: Can handle very large contexts efficiently
- **Quantization**: Q5_K_M recommended for quality/speed balance

#### Troubleshooting for H100

**Out of Memory Errors**:
1. **Reduce Context Window**: Lower `LLM_N_CTX` (e.g., 65536 instead of 131072)
2. **Use Lower Quantization**: Q4 instead of Q5 for GGUF models
3. **Use MoE Models**: Qwen3-30B-A3B uses less VRAM than dense 32B

**Model Not Found** (Transformers models):
- Model is downloaded to a directory (not a single file)
- Path points to the model directory
- `LLM_BACKEND=transformers` is set

**Slow Inference**:
- Ensure GPU is being used (`nvidia-smi` should show GPU usage)
- Check that `LLM_N_GPU_LAYERS=-1` for full GPU offload
- Consider using MoE models for faster inference

## CPU-Only Setup

If you don't have a GPU or want to use CPU:

**Configuration**: Use `cpu` profile:

```bash
# Linux/Mac
./scripts/setup_env.sh cpu

# Windows PowerShell
.\scripts\setup_env.ps1 cpu
```

**Or manually configure**:
```bash
LLM_N_GPU_LAYERS=0
LLM_N_CTX=16384
```

**Recommended Models**:
- Qwen2.5-7B-Instruct Q4_K_M (slower but works)
- Smaller models are better for CPU-only

**Performance**: Expect 2-10x slower than GPU inference. Use smaller context windows for better performance.

## Environment Variables Reference

### LLM Configuration

| Variable | Description | Default | Examples |
|----------|-------------|---------|----------|
| `LLM_MODEL_PATH` | Path to model file/directory | (required) | `./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf` |
| `LLM_BACKEND` | Backend type | `auto` | `auto`, `llama_cpp`, `transformers` |
| `LLM_N_CTX` | Context window size | `131072` | `32768`, `65536`, `131072` |
| `LLM_N_GPU_LAYERS` | GPU layers (-1=auto, 0=CPU) | `-1` | `-1`, `0`, `35`, `60` |
| `LLM_TEMPERATURE` | Sampling temperature | `0.7` | `0.0`-`1.0` |
| `LLM_TOP_P` | Top-p sampling | `0.9` | `0.0`-`1.0` |

### API Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Bind address | `0.0.0.0` |
| `API_PORT` | Port number | `8000` |
| `API_RELOAD` | Auto-reload on changes | `false` |

### Storage Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AUDIO_STORAGE_PATH` | Audio storage directory | `audio_storage` |
| `MIDI_STORAGE_PATH` | MIDI storage directory | `midi_storage` |
| `NOTATION_STORAGE_PATH` | Notation storage directory | `notation_storage` |

### Debug Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_TOOL_CALLS` | Verbose tool calling logs | `false` |

## Model Selection Guide

### By VRAM

| Hardware | Recommended Models | Context |
|----------|-------------------|---------|
| CPU-only | Qwen2.5-7B Q4 | 16K |
| 8GB VRAM | Qwen2.5-7B Q4 | 32K |
| 16GB VRAM | Qwen2.5-14B Q4/Q5, Llama 3.3 70B Q4 | 32K-64K |
| 24GB VRAM | Qwen2.5-14B Q5, Llama 3.3 70B Q5 | 64K |
| 40GB VRAM | Qwen3-30B-A3B MoE, Llama 3.3 70B Q5 | 128K |
| 80GB VRAM | Qwen3-32B, Qwen3-30B-A3B MoE | 128K+ |

### By Use Case

- **Best Function Calling**: Qwen2.5-7B/14B or Qwen3 models
- **Largest Context**: Qwen3-32B (128K native)
- **Fastest Inference**: Qwen3-30B-A3B MoE (only ~3.3B active params)
- **Best Quality**: Qwen3-32B or Llama 3.3 70B Q5

## Troubleshooting

### Out of Memory (OOM) Errors

1. **Reduce context window**:
   ```bash
   LLM_N_CTX=16384  # Instead of 32768
   ```

2. **Use lower quantization**:
   - Switch from Q5 to Q4
   - Or use a smaller model

3. **Reduce GPU layers** (for llama_cpp):
   ```bash
   LLM_N_GPU_LAYERS=20  # Instead of -1
   ```

4. **Use CPU for some layers**:
   ```bash
   LLM_N_GPU_LAYERS=30  # Partial GPU offload
   ```

### Model Not Found

- **GGUF models**: Ensure path points to `.gguf` file
- **Transformers models**: Ensure path points to model directory (not file)
- **Check path**: Use absolute path or relative to project root

### Slow Inference

1. **Check GPU usage**: `nvidia-smi` should show GPU activity
2. **Ensure GPU layers**: `LLM_N_GPU_LAYERS=-1` for full GPU offload
3. **Use smaller context**: Reduce `LLM_N_CTX`
4. **Consider MoE models**: Qwen3-30B-A3B is faster than dense 32B

### Backend Detection Issues

- **Explicit backend**: Set `LLM_BACKEND=llama_cpp` or `LLM_BACKEND=transformers`
- **Check model format**: GGUF files → llama_cpp, HuggingFace directories → transformers

## Remote Execution

For remote execution (SSH port forwarding):

1. **API Host**: Already set to `0.0.0.0` (works for remote access)
2. **SSH Tunnel**: `ssh -L 8000:localhost:8000 user@remote-server`
3. **Access**: `http://localhost:8000` from local machine

All paths are configurable, no hardcoded localhost dependencies.

## Examples

### Example 1: CPU-Only Setup

```bash
# Setup CPU-only config
./scripts/setup_env.sh cpu

# Download model
python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models

# Run
python run.py
```

### Example 2: RTX 3060Ti Development Setup

```bash
# Setup small GPU config
./scripts/setup_env.sh small

# Download model
python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models

# Run
python run.py
```

### Example 3: H100 Production Setup

```bash
# Copy large GPU config
cp .env.example.large .env

# Download model
python scripts/download_model.py qwen3-32b-instruct -o ./models

# Edit .env
LLM_MODEL_PATH=./models/Qwen_Qwen3-32B-Instruct
LLM_BACKEND=transformers
LLM_N_CTX=131072
LLM_N_GPU_LAYERS=-1

# Run
python run.py
```

## Next Steps

- See [MODEL_RECOMMENDATIONS.md](./MODEL_RECOMMENDATIONS.md) for model details
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment options
- Check GPU usage: `nvidia-smi` or `watch -n 1 nvidia-smi`
