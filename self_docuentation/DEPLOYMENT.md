# Deployment Reference

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- LLM model file (GGUF format)
- At least 8GB RAM (16GB+ recommended for 70B models)

### Quick Start

```bash
# Download model
python scripts/download_model.py llama-3.1-8b-instruct-q4 -o ./models

# Set model filename (if different from default)
export LLM_MODEL_FILE=Llama-3.1-8B-Instruct-Q4_K_M.gguf

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Direct Docker

```bash
# Build
docker build -t zikos:latest .

# Run
docker run -d \
  --name zikos \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/audio_storage:/app/audio_storage \
  -v $(pwd)/midi_storage:/app/midi_storage \
  -v $(pwd)/notation_storage:/app/notation_storage \
  -e LLM_MODEL_PATH=/app/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf \
  zikos:latest
```

## Environment Variables

- `LLM_MODEL_PATH`: Path to GGUF model file (required)
- `LLM_N_CTX`: Context window size (default: 131072)
- `LLM_N_GPU_LAYERS`: GPU layers (default: 0, CPU only)
- `LLM_TEMPERATURE`: Sampling temperature (default: 0.7)
- `LLM_TOP_P`: Top-p sampling (default: 0.9)
- `API_HOST`: Bind address (default: 0.0.0.0)
- `API_PORT`: Port number (default: 8000)
- `AUDIO_STORAGE_PATH`: Audio storage directory (default: /app/audio_storage)
- `MIDI_STORAGE_PATH`: MIDI storage directory (default: /app/midi_storage)
- `NOTATION_STORAGE_PATH`: Notation storage directory (default: /app/notation_storage)

## GPU Support

To enable GPU acceleration:
1. Use CUDA-enabled base image or install CUDA libraries
2. Set `LLM_N_GPU_LAYERS` to positive number (e.g., 35 for full GPU offload on 8B models)

Example Dockerfile modification:
```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS base
# ... rest of Dockerfile
```

Run with:
```bash
docker run --gpus all ...
```

## Remote Deployment

### Deploy to Remote Server
```bash
# Copy files
rsync -avz --exclude 'node_modules' --exclude '__pycache__' \
  --exclude '.git' --exclude '*.pyc' \
  ./ user@remote-server:/path/to/zikos/

# SSH and build
ssh user@remote-server
cd /path/to/zikos
docker-compose build
docker-compose up -d
```

### SSH Tunnel (Alternative)
```bash
ssh -L 8000:localhost:8000 user@remote-server
# Then access via http://localhost:8000
```

## Storage Volumes

Mounted volumes:
- `./models` → `/app/models` (read-only, for model files)
- `./audio_storage` → `/app/audio_storage` (user uploads)
- `./midi_storage` → `/app/midi_storage` (generated MIDI files)
- `./notation_storage` → `/app/notation_storage` (generated notation files)

Create directories:
```bash
mkdir -p models audio_storage midi_storage notation_storage
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs zikos
```

### Model not found
- Ensure model file exists in `./models` directory
- Check `LLM_MODEL_PATH` environment variable
- Verify volume mount: `-v $(pwd)/models:/app/models:ro`

### Out of memory
- Use smaller model (8B instead of 70B)
- Reduce `LLM_N_CTX` context window
- Ensure host has enough RAM

### FluidSynth/SoundFont issues
Container includes `fluid-soundfont-gm` by default. For different SoundFont, mount as volume and update configuration.

## Production Considerations

1. **Security**:
   - Restrict CORS origins (currently allows all)
   - Use HTTPS with reverse proxy
   - Set up proper authentication if needed

2. **Performance**:
   - Use GPU acceleration if available
   - Consider larger model with more RAM
   - Monitor resource usage

3. **Reliability**:
   - Set up health checks (already included)
   - Use `restart: unless-stopped` in docker-compose
   - Monitor logs and set up alerting

4. **Backup**:
   - Regularly backup storage volumes
   - Keep model files in safe location
