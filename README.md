# Zikos - AI Music Teacher POC

A proof-of-concept AI music teacher that combines LLM chat interaction with audio analysis and MIDI generation for personalized music instruction.

## Status

🚧 Early development - POC implementation - Vibe-coding involved - Not to be used as-is


## Quick Overview

- **Audio Input**: User recordings analyzed via signal processing tools
- **LLM**: Phi-3 Mini (recommended for CPU) or Mistral 7B (recommended for GPU) with good function calling support
- **Output**: Text feedback + MIDI-generated musical examples with notation
- **Architecture**: FastAPI backend + TypeScript frontend
- **Backends**: Supports both llama-cpp-python (GGUF) and HuggingFace Transformers (safetensors)

## Hardware Support

Zikos tries to support a wide range of hardware configurations:

- **CPU-only**: Works without GPU (slow, but functional) - Phi-3 Mini recommended (or Llama 3.2 8B if you have enough RAM)
- **Small GPU (8GB VRAM)**: RTX 3060Ti, RTX 3070, etc. - Mistral 7B recommended
- **Medium GPU (16-24GB VRAM)**: RTX 3090, RTX 4090, etc. - Mistral 7B or larger models
- **Large GPU (80GB+ VRAM)**: H100, A100, etc. - Larger models with extended context

## Setup
### Prerequisites

- Python 3.11+
- FFmpeg (for audio preprocessing)
- LLM model file (GGUF or HuggingFace Transformers format) - see [Downloading Models](#downloading-models) below
- GPU recommended (8GB+ VRAM) but CPU-only is supported

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install .

# Install JavaScript dependencies (for TypeScript frontend)
npm install
npm run build  # Build TypeScript to JavaScript

# Set environment variables
# Copy .env.example to .env and edit with your settings
cp .env.example .env  # On Windows: copy .env.example .env
# Edit .env with your settings (especially LLM_MODEL_PATH)
```

## Environment Variables

Zikos can be configured via environment variables. Copy `.env.example` to `.env` and adjust values for your setup.

### Downloading Models

You can download models using the provided helper script. See [MODEL_RECOMMENDATIONS.md](./MODEL_RECOMMENDATIONS.md) for detailed recommendations.

```bash
# List available models
python scripts/download_model.py --list
python scripts/download_model.py phi-3-mini-q4 -o ./models
python scripts/download_model.py mistral-7b-instruct-v0.3-q4 -o ./models

# With Hugging Face token (for private models)
python scripts/download_model.py qwen3-32b-instruct -t YOUR_TOKEN
```

The script supports both GGUF (llama-cpp-python) and Transformers (HuggingFace) formats. After downloading, the `.env` file created by the setup script will be configured automatically, or you can set `LLM_MODEL_PATH` manually:

```bash
# For GGUF models (examples)
export LLM_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
export LLM_MODEL_PATH=./models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
```

### System Prompt KV Cache (llama-cpp-python only)

For faster server startup, you can pre-compute the system prompt KV cache. This avoids reprocessing the system prompt for every conversation:

```bash
# Generate cache manually
python scripts/generate_system_prompt_cache.py --model-path ./models/your-model.gguf

# Or set SYSTEM_PROMPT_CACHE_PATH in .env - cache will be auto-generated if missing
export SYSTEM_PROMPT_CACHE_PATH=./models/your-model_system_cache.bin
```

The cache file can be generated in CI and included in deployments. If `SYSTEM_PROMPT_CACHE_PATH` is set but the file doesn't exist, it will be automatically generated on startup.

**Note**: The script requires `huggingface_hub` for Transformers models. Install with:
```bash
# Recommended: install model download helpers
pip install -e ".[model-download]"

# Or install individually
pip install huggingface_hub
```

## Run

```bash
python run.py
```

API will be available at `http://localhost:8000`

## Docker

Zikos can be run using Docker, which handles all dependencies and setup automatically.

### Prerequisites

- Docker and Docker Compose installed
- LLM model file downloaded to `./models/` directory (see [Downloading Models](#downloading-models))

### Using Docker Compose (Recommended)

The easiest way to run Zikos with Docker:

```bash
# Set the model filename (optional, defaults to Phi-3-mini-4k-instruct-q4.gguf)
export LLM_MODEL_FILE=Phi-3-mini-4k-instruct-q4.gguf
export LLM_MODEL_FILE=mistral-7b-instruct-v0.3.Q4_K_M.gguf

# Build and start the container
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The API will be available at `http://localhost:8000`. The container automatically:
- Builds the frontend TypeScript code
- Mounts your `./models` directory (read-only) for model access
- Creates and mounts storage directories for audio, MIDI, and notation files
- Sets up environment variables with sensible defaults

### Using Docker Directly

```bash
# Build the image
docker build -t zikos .

# Run the container
docker run -d \
  --name zikos \
  -p 8000:8000 \
  -v ./models:/app/models:ro \
  -v ./audio_storage:/app/audio_storage \
  -v ./midi_storage:/app/midi_storage \
  -v ./notation_storage:/app/notation_storage \
  -e LLM_MODEL_PATH=/app/models/Phi-3-mini-4k-instruct-q4.gguf \
  -e LLM_N_CTX=32768 \
  -e LLM_N_GPU_LAYERS=0 \
  zikos
```

### Docker Configuration

The Docker setup uses volumes to persist data:
- `./models` → `/app/models` (read-only): Model files
- `./audio_storage` → `/app/audio_storage`: Uploaded audio files
- `./midi_storage` → `/app/midi_storage`: Generated MIDI files
- `./notation_storage` → `/app/notation_storage`: Generated notation files

Environment variables can be customized in `docker-compose.yml` or passed via `-e` flags when using `docker run`. See [Environment Variables](#environment-variables) for available options.

**Note**: For GPU support, you'll need to configure Docker with GPU access (e.g., `--gpus all` flag or Docker Compose GPU configuration) and adjust `LLM_N_GPU_LAYERS` accordingly.

## Development
### Dependencies

- **LLM**: Phi-3 Mini (recommended for CPU), Mistral 7B (recommended for GPU), or similar models, via dual backend support
  - **llama-cpp-python**: For GGUF models (Phi-3, Mistral, Llama, Qwen)
  - **HuggingFace Transformers**: For safetensors models (Qwen3)
- **Audio Processing**: librosa, torchaudio, soundfile
- **MIDI**: Music21 for processing, FluidSynth for synthesis
- **Backend**: FastAPI with WebSocket support
- **Frontend**: TypeScript + Web Audio API

### Code Quality

The project uses:
- **ruff**: Fast Python linter
- **black**: Code formatter
- **mypy**: Static type checker
- **pytest**: Testing framework with coverage

### Project Structure

```
zikos/
├── backend/
│   └── zikos/          # Python backend code
│       ├── api/        # FastAPI routes
│       ├── mcp/        # MCP tools and server
│       ├── services/   # Business logic
│       ├── config.py   # Configuration
│       └── main.py     # FastAPI app
├── frontend/           # TypeScript/HTML frontend
│   ├── src/            # TypeScript source files
│   ├── dist/           # Compiled JavaScript (generated)
│   └── index.html      # Main HTML file
├── tests/              # Test code
├── scripts/            # Utility scripts (model download, env setup)
├── CONFIGURATION.md    # Hardware-specific configuration guide (includes H100 optimization)
├── MODEL_RECOMMENDATIONS.md # Model recommendations
├── DESIGN.md           # Architecture design and future roadmap
├── TOOLS.md            # MCP tools specification
└── SYSTEM_PROMPT.md    # LLM system prompt
```

### Python env setup
```bash
pip install .[dev]

# Optional: generate a pinned requirements.txt for reproducible builds
pip-compile pyproject.toml -o requirements.txt
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks (runs checks before commit)
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Testing

This project follows Test-Driven Development (TDD) principles with comprehensive test coverage.

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test API endpoints and service interactions
- **Coverage target**: Minimum 80% code coverage

**Note**: Comprehensive tests (LLM inference, heavy audio processing) and integration tests are excluded from default pytest runs and pre-commit hooks to keep commit times reasonable. These tests are marked as `comprehensive` or `integration` and require model files or significant resources. LLM integration tests verify real tool calling functionality. These are critical for catching bugs that mocked tests miss.

Run tests:
```bash
pytest -m not comprehensive  # Run all but comprehensive tests
pytest -m integration    # Run integration tests
pytest -m ""             # Run all tests including comprehensive and integration
```

### Continuous Integration

The project uses GitHub Actions for CI/CD. The workflow (`.github/workflows/ci.yml`) runs automatically on pushes and pull requests to `main` and `develop` branches.

#### CI Jobs

1. **Test** (Python 3.11, 3.12, 3.13)
   - Runs unit tests with coverage (minimum 75% required)
   - Runs integration tests (excluding comprehensive tests)
   - Uploads coverage to Codecov (Python 3.13 only)
   - Installs system dependencies (libsndfile, ffmpeg, fluidsynth, etc.)

2. **Lint**
   - Runs `ruff` for linting
   - Runs `black --check` for code formatting
   - Runs `mypy` for type checking

3. **TypeScript Type Check**
   - Runs TypeScript type checking
   - Runs ESLint for frontend code quality

4. **Frontend Tests**
   - Runs frontend test suite with coverage
   - Uploads coverage to Codecov

All jobs must pass for a PR to be mergeable. The CI ensures code quality, type safety, and test coverage across multiple Python versions and the frontend.
