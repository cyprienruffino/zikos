# Deployment Guide

This guide covers deploying Zikos using Docker.

## Prerequisites

- Docker and Docker Compose installed
- LLM model file (GGUF format) - see [Downloading Models](#downloading-models) below
- At least 8GB RAM (16GB+ recommended for 70B models)

## Quick Start

### 1. Download a Model

Download a model to a local directory (e.g., `./models`):

```bash
# Download Llama 3.1 8B (recommended)
python scripts/download_model.py llama-3.1-8b-instruct-q4 -o ./models

# Or download Llama 3.3 70B (requires 16GB+ RAM)
python scripts/download_model.py llama-3.3-70b-instruct-q4 -o ./models
```

### 2. Build and Run with Docker Compose

```bash
# Set the model filename (if different from default)
export LLM_MODEL_FILE=Llama-3.1-8B-Instruct-Q4_K_M.gguf

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The application will be available at `http://localhost:8000`

### 3. Run with Docker Directly

```bash
# Build the image
docker build -t zikos:latest .

# Run the container
docker run -d \
  --name zikos \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/audio_storage:/app/audio_storage \
  -v $(pwd)/midi_storage:/app/midi_storage \
  -v $(pwd)/notation_storage:/app/notation_storage \
  -e LLM_MODEL_PATH=/app/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf \
  zikos:latest

# View logs
docker logs -f zikos

# Stop the container
docker stop zikos
docker rm zikos
```

## Configuration

### Environment Variables

You can configure the application using environment variables in `docker-compose.yml` or via `-e` flags:

- `LLM_MODEL_PATH`: Path to the GGUF model file (required)
- `LLM_N_CTX`: Context window size (default: 4096)
- `LLM_N_GPU_LAYERS`: Number of GPU layers (default: 0, CPU only)
- `LLM_TEMPERATURE`: Sampling temperature (default: 0.7)
- `LLM_TOP_P`: Top-p sampling (default: 0.9)
- `API_HOST`: Bind address (default: 0.0.0.0)
- `API_PORT`: Port number (default: 8000)
- `AUDIO_STORAGE_PATH`: Audio storage directory (default: /app/audio_storage)
- `MIDI_STORAGE_PATH`: MIDI storage directory (default: /app/midi_storage)
- `NOTATION_STORAGE_PATH`: Notation storage directory (default: /app/notation_storage)

### GPU Support

To enable GPU acceleration for llama-cpp-python, you'll need to:

1. Use a CUDA-enabled base image or install CUDA libraries
2. Set `LLM_N_GPU_LAYERS` to a positive number (e.g., 35 for full GPU offload on 8B models)

Example Dockerfile modification for GPU:

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS base
# ... rest of Dockerfile
```

Then run with:

```bash
docker run --gpus all ...
```

## Remote Deployment

### Deploy to Remote Server

1. **Copy files to remote server:**

```bash
# On your local machine
rsync -avz --exclude 'node_modules' --exclude '__pycache__' \
  --exclude '.git' --exclude '*.pyc' \
  ./ user@remote-server:/path/to/zikos/
```

2. **SSH into remote server and build:**

```bash
ssh user@remote-server
cd /path/to/zikos
docker-compose build
docker-compose up -d
```

3. **Access from local browser:**

If the remote server has a public IP, you can access it directly:
- `http://<remote-ip>:8000`

For production, consider:
- Using a reverse proxy (nginx) with SSL/TLS
- Restricting CORS origins in the application
- Setting up firewall rules
- Using a process manager (systemd) to keep the container running

### SSH Tunnel (Alternative)

If you can't expose port 8000 directly:

```bash
# On your local machine
ssh -L 8000:localhost:8000 user@remote-server

# Then access via http://localhost:8000
```

## Storage Volumes

The following directories are mounted as volumes to persist data:

- `./models` → `/app/models` (read-only, for model files)
- `./audio_storage` → `/app/audio_storage` (user uploads)
- `./midi_storage` → `/app/midi_storage` (generated MIDI files)
- `./notation_storage` → `/app/notation_storage` (generated notation files)

Make sure these directories exist and have proper permissions:

```bash
mkdir -p models audio_storage midi_storage notation_storage
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs zikos
```

### Model not found

Ensure:
1. Model file exists in the `./models` directory
2. `LLM_MODEL_PATH` environment variable points to the correct file
3. Volume mount is correct: `-v $(pwd)/models:/app/models:ro`

### Out of memory

- Use a smaller model (8B instead of 70B)
- Reduce `LLM_N_CTX` context window
- Ensure the host has enough RAM

### FluidSynth/SoundFont issues

The container includes `fluid-soundfont-gm` by default. If you need a different SoundFont, mount it as a volume and update the application configuration.

## Production Considerations

1. **Security:**
   - Restrict CORS origins (currently allows all)
   - Use HTTPS with a reverse proxy
   - Set up proper authentication if needed

2. **Performance:**
   - Use GPU acceleration if available
   - Consider using a larger model with more RAM
   - Monitor resource usage

3. **Reliability:**
   - Set up health checks (already included)
   - Use `restart: unless-stopped` in docker-compose
   - Monitor logs and set up alerting

4. **Backup:**
   - Regularly backup storage volumes
   - Keep model files in a safe location
