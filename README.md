# Zikos - AI Music Teacher POC

A proof-of-concept AI music teacher that combines LLM chat interaction with audio analysis and MIDI generation for personalized music instruction.

## Quick Overview

- **Audio Input**: User recordings analyzed via signal processing tools
- **LLM**: Llama 3.1/3.2 8B-Instruct with function calling support
- **Output**: Text feedback + MIDI-generated musical examples with notation
- **Architecture**: FastAPI backend + React/Vue frontend

## Key Technologies

- **LLM**: Llama 3.1/3.2 8B-Instruct via llama-cpp-python
- **Audio Processing**: librosa, torchaudio, soundfile
- **MIDI**: Music21 for processing, FluidSynth for synthesis
- **Backend**: FastAPI with WebSocket support
- **Frontend**: React/Vue + Web Audio API (to be implemented)

## Setup

### Prerequisites

- Python 3.11+
- LLM model file (GGUF format)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install-dev  # Installs with dev dependencies

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

### Development

```bash
# Run tests
make test          # Run all tests
make test-cov      # Run tests with coverage
make test-fast     # Run tests without coverage (faster)

# Code quality
make lint          # Run ruff linter
make format        # Format code with black
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
uvicorn src.zikos.main:app --reload
```

API will be available at `http://localhost:8000`

## Project Structure

```
zikos/
├── src/zikos/
│   ├── api/           # FastAPI routes
│   ├── mcp/           # MCP tools and server
│   ├── services/      # Business logic
│   ├── config.py      # Configuration
│   └── main.py        # FastAPI app
├── DESIGN.md          # Architecture design
├── TOOLS.md           # MCP tools specification
├── SYSTEM_PROMPT.md   # LLM system prompt
├── IMPLEMENTATION_NOTES.md  # Implementation details
└── requirements.txt   # Python dependencies
```

## Documentation

See [DESIGN.md](./DESIGN.md) for detailed architecture, implementation decisions, and future work.

## Testing

This project follows Test-Driven Development (TDD) principles with comprehensive test coverage.

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test API endpoints and service interactions
- **Coverage target**: Minimum 80% code coverage

Run tests:
```bash
make test-cov  # With coverage report
make test      # Standard test run
```

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
