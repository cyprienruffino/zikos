# Zikos - AI Music Teacher POC

A proof-of-concept AI music teacher that combines LLM chat interaction with audio analysis and MIDI generation for personalized music instruction.

## Quick Overview

- **Audio Input**: User recordings analyzed via signal processing tools
- **LLM**: Qwen2.5/Qwen3 models with excellent function calling support (or Llama 3.3 70B)
- **Output**: Text feedback + MIDI-generated musical examples with notation
- **Architecture**: FastAPI backend + TypeScript frontend
- **Backends**: Supports both llama-cpp-python (GGUF) and HuggingFace Transformers (safetensors)

## Key Technologies

- **LLM**: Qwen2.5-7B/14B (recommended) or Qwen3-32B (for H100) via dual backend support
  - **llama-cpp-python**: For GGUF models (Qwen2.5, Llama 3.3)
  - **HuggingFace Transformers**: For safetensors models (Qwen3)
- **Audio Processing**: librosa, torchaudio, soundfile
- **MIDI**: Music21 for processing, FluidSynth for synthesis
- **Backend**: FastAPI with WebSocket support
- **Frontend**: TypeScript + Web Audio API

## Setup

### Prerequisites

- Python 3.11+
- FFmpeg (for audio preprocessing) - see [FFmpeg Installation](#ffmpeg-installation) below
- LLM model file (GGUF or HuggingFace Transformers format) - see [Downloading Models](#downloading-models) below
- GPU recommended (8GB+ VRAM) but CPU-only is supported - see [CONFIGURATION.md](./CONFIGURATION.md)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
make install-dev  # Installs with dev dependencies

# Install JavaScript dependencies (for TypeScript frontend)
npm install
npm run build  # Build TypeScript to JavaScript

# Or install production only (without heavy ML libraries)
make install

# Or install with ML libraries (for full functionality)
pip install -e ".[ml]"

# Or install everything
pip install -e ".[dev,ml]"

# Set environment variables
# Choose based on your hardware (see CONFIGURATION.md for details):

# Option 1: Use setup script (recommended)
# Linux/Mac:
./scripts/setup_env.sh cpu     # CPU-only (no GPU), super slow
./scripts/setup_env.sh small   # For ~RTX 3060Ti / 8GB VRAM
./scripts/setup_env.sh medium  # For ~RTX 4090 / 24GB VRAM
./scripts/setup_env.sh large   # For ~H100 / 80GB VRAM

# Windows PowerShell:
.\scripts\setup_env.ps1 cpu
.\scripts\setup_env.ps1 small
.\scripts\setup_env.ps1 medium
.\scripts\setup_env.ps1 large

# Option 2: Manual setup
# See CONFIGURATION.md for hardware-specific examples
# Edit .env with your settings (especially LLM_MODEL_PATH)
```

### FFmpeg Installation

FFmpeg is required for audio preprocessing (converting various audio formats to WAV).

**Linux:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) or use:
```powershell
choco install ffmpeg
```

### Downloading Models

You can download models using the provided helper script. See [MODEL_RECOMMENDATIONS.md](./MODEL_RECOMMENDATIONS.md) for detailed recommendations.

```bash
# List available models
python scripts/download_model.py --list

# Recommended models by hardware:
# CPU-only or Small GPU (8GB VRAM):
python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models

# Medium GPU (16-24GB VRAM):
python scripts/download_model.py qwen2.5-14b-instruct-q4 -o ./models

# Large GPU (80GB+ VRAM, H100):
python scripts/download_model.py qwen3-32b-instruct -o ./models

# Download to a specific directory
python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models

# With Hugging Face token (for private models)
python scripts/download_model.py qwen3-32b-instruct -t YOUR_TOKEN
```

The script supports both GGUF (llama-cpp-python) and Transformers (HuggingFace) formats. After downloading, the `.env` file created by the setup script will be configured automatically, or you can set `LLM_MODEL_PATH` manually:

```bash
# For GGUF models
export LLM_MODEL_PATH=./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf

# For Transformers models (Qwen3)
export LLM_MODEL_PATH=./models/Qwen_Qwen3-32B-Instruct
export LLM_BACKEND=transformers
```

**Note**: The script requires `huggingface_hub` for Transformers models. Install with:
```bash
# Recommended: install model download helpers
pip install -e ".[model-download]"

# Or install individually
pip install huggingface_hub
```

### Development

```bash
# Run tests
make test          # Run all tests
make test-cov      # Run tests with coverage
make test-fast     # Run tests without coverage (faster)

# Code quality
make lint          # Run linters (ruff + eslint)
make lint-js       # Run JavaScript linter only
make format        # Format code (black + prettier)
make format-js     # Format JavaScript code only
make format-check  # Check formatting without changing files
make type-check    # Run mypy type checker
make check         # Run all checks (lint + format-check + type-check)

# Run application
make run
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks (runs checks before commit)
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Run

```bash
python run.py
```

Or with uvicorn directly:

```bash
uvicorn zikos.main:app --reload --app-dir backend
```

API will be available at `http://localhost:8000`

## Project Structure

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
├── SYSTEM_PROMPT.md    # LLM system prompt
└── requirements.txt    # Python dependencies
```

## Documentation

- [CONFIGURATION.md](./CONFIGURATION.md) - **Hardware-specific configuration guide** (CPU, Small/Medium/Large GPU, including H100 optimization)
- [MODEL_RECOMMENDATIONS.md](./MODEL_RECOMMENDATIONS.md) - Model recommendations and function calling support
- [DESIGN.md](./DESIGN.md) - Architecture design, implementation decisions, and future roadmap
- [TOOLS.md](./TOOLS.md) - MCP tools specification and API reference
- [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md) - LLM system prompt

## Testing

This project follows Test-Driven Development (TDD) principles with comprehensive test coverage.

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test API endpoints and service interactions
- **Coverage target**: Minimum 80% code coverage

**Note**: Comprehensive tests (LLM inference, heavy audio processing) and integration tests are excluded from default pytest runs and pre-commit hooks to keep commit times reasonable. These tests are marked as `comprehensive` or `integration` and require model files or significant resources. See [DEVELOPMENT.md](./DEVELOPMENT.md) for details.

Run tests:
```bash
make test-cov  # With coverage report (excludes comprehensive and integration tests)
make test      # Standard test run (excludes comprehensive and integration tests)
pytest -m comprehensive  # Run comprehensive tests (requires model file for LLM tests)
pytest -m integration    # Run integration tests
pytest -m ""             # Run all tests including comprehensive and integration
```

**Important**: LLM integration tests verify real tool calling functionality. These are critical for catching bugs that mocked tests miss. See [DEVELOPMENT.md](./DEVELOPMENT.md#running-llm-integration-tests) for detailed instructions on when and how to run them.

## Code Quality

The project uses:
- **ruff**: Fast Python linter
- **black**: Code formatter
- **mypy**: Static type checker
- **pytest**: Testing framework with coverage

All checks can be run with:
```bash
make check
```

## Hardware Support

Zikos supports a wide range of hardware configurations:

- **CPU-only**: Works without GPU (slower, but functional)
- **Small GPU (8GB VRAM)**: RTX 3060Ti, RTX 3070, etc. - Qwen2.5-7B recommended
- **Medium GPU (16-24GB VRAM)**: RTX 3090, RTX 4090, etc. - Qwen2.5-14B or Llama 3.3 70B
- **Large GPU (80GB+ VRAM)**: H100, A100, etc. - Qwen3-32B with 128K context window

See [CONFIGURATION.md](./CONFIGURATION.md) for detailed setup instructions for each hardware profile.

## Status

🚧 Early development - POC implementation - Fully vibe-coded
