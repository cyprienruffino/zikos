# Zikos - AI Music Teacher POC

A proof-of-concept AI music teacher that combines LLM chat interaction with audio analysis and MIDI generation for personalized music instruction.

## Quick Overview

- **Audio Input**: User recordings analyzed via signal processing tools
- **LLM**: Llama 3.1/3.2 8B-Instruct (or Llama 3.3 70B) with function calling support
- **Output**: Text feedback + MIDI-generated musical examples with notation
- **Architecture**: FastAPI backend + React/Vue frontend

## Key Technologies

- **LLM**: Llama 3.1/3.2 8B-Instruct (or Llama 3.3 70B) via llama-cpp-python
- **Audio Processing**: librosa, torchaudio, soundfile
- **MIDI**: Music21 for processing, FluidSynth for synthesis
- **Backend**: FastAPI with WebSocket support
- **Frontend**: React/Vue + Web Audio API (to be implemented)

## Setup

### Prerequisites

- Python 3.11+
- LLM model file (GGUF format) - see [Downloading Models](#downloading-models) below

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
cp .env.example .env
# Edit .env with your settings
```

### Downloading Models

You can download Llama models using the provided helper script:

```bash
# List available models
python scripts/download_model.py --list

# Download a model (recommended: 8B Q4_K_M for balance of quality and size)
python scripts/download_model.py llama-3.1-8b-instruct-q4

# Or download Llama 3.3 70B (requires 16GB+ RAM, much larger but more capable)
python scripts/download_model.py llama-3.3-70b-instruct-q4

# Or use the Makefile target
make download-model MODEL=llama-3.1-8b-instruct-q4

# Download to a specific directory
python scripts/download_model.py llama-3.1-8b-instruct-q4 -o ./models

# With Hugging Face token (for private models)
python scripts/download_model.py llama-3.1-8b-instruct-q4 -t YOUR_TOKEN
```

The script will download the model to `~/.zikos/models/` by default. After downloading, set the `LLM_MODEL_PATH` environment variable or add it to your `.env` file:

```bash
export LLM_MODEL_PATH=~/.zikos/models/Llama-3.1-8B-Instruct-Q4_K_M.gguf
```

**Note**: The script requires either `huggingface_hub` (recommended) or `requests`. Install with:
```bash
# Recommended: install model download helpers
pip install -e ".[model-download]"

# Or install individually
pip install huggingface_hub  # Recommended
# or
pip install requests  # Fallback option
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
├── DESIGN.md           # Architecture design
├── TOOLS.md            # MCP tools specification
├── SYSTEM_PROMPT.md    # LLM system prompt
├── AUDIO_ANALYSIS_TOOLS.md # Comprehensive audio analysis tools catalog
├── FUTURE_FEATURES.md  # Future features and roadmap
└── requirements.txt    # Python dependencies
```

## Documentation

- [DESIGN.md](./DESIGN.md) - Architecture design and implementation decisions
- [AUDIO_ANALYSIS_TOOLS.md](./AUDIO_ANALYSIS_TOOLS.md) - Comprehensive catalog of audio analysis tools and techniques
- [FUTURE_FEATURES.md](./FUTURE_FEATURES.md) - Future features roadmap and planned enhancements
- [TOOLS.md](./TOOLS.md) - MCP tools specification
- [SYSTEM_PROMPT.md](./SYSTEM_PROMPT.md) - LLM system prompt

## Testing

This project follows Test-Driven Development (TDD) principles with comprehensive test coverage.

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test API endpoints and service interactions
- **Coverage target**: Minimum 80% code coverage

**Note**: LLM service tests are excluded from coverage calculations and CI runs. These tests are marked as `expensive` and `llama` and require model files. See [DEVELOPMENT.md](./DEVELOPMENT.md) for details.

Run tests:
```bash
make test-cov  # With coverage report (excludes LLM tests)
make test      # Standard test run (excludes LLM tests)
pytest -m llama  # Run LLM integration tests (requires model file)
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

## Status

🚧 Early development - POC implementation
