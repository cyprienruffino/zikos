# Development Guide

## Development Environment Setup

### Prerequisites

- Python 3.11 or higher
- `make` (optional, but recommended for convenience)

### Initial Setup

```bash
# Clone repository
git clone <repo-url>
cd zikos

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
make install-dev

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Running Tests

```bash
# Run all tests with coverage
make test-cov

# Run tests without coverage (faster)
make test-fast

# Run specific test file
pytest tests/unit/test_config.py

# Run tests matching pattern
pytest -k "test_config"

# Run with verbose output
pytest -v

# Run tests in parallel (faster)
pytest -n auto
```

### Code Quality Checks

```bash
# Run all checks (lint + format-check + type-check)
make check

# Individual checks
make lint          # Run ruff linter
make format-check  # Check code formatting
make format        # Auto-format code
make type-check    # Run mypy type checker
```

### Pre-commit Hooks

Pre-commit hooks automatically run checks before each commit:

- Trailing whitespace removal
- End of file fixes
- YAML/JSON/TOML validation
- Black formatting
- Ruff linting
- MyPy type checking
- **Fast unit tests only** (excludes `slow`, `integration`, `expensive`, and `llama` tests)

**Important**: The pre-commit hook runs only fast unit tests. Slow tests (like audio processing tests that do real analysis) are excluded to keep commit times reasonable. These tests are still run in CI and can be run manually with `pytest -m slow` or `pytest -m integration`.

To run hooks manually:
```bash
pre-commit run --all-files
```

## Testing Strategy

### Test-Driven Development (TDD)

1. **Write failing test first**
   ```python
   def test_new_feature():
       result = new_function()
       assert result == expected_value
   ```

2. **Implement minimal code to pass**
   ```python
   def new_function():
       return expected_value
   ```

3. **Refactor while keeping tests green**

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── unit/               # Unit tests (fast, isolated)
│   ├── test_config.py
│   └── test_mcp_tools.py
└── integration/        # Integration tests (slower, test interactions)
    └── test_api.py
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_fast_unit_test():
    ...

@pytest.mark.integration
def test_api_endpoint():
    ...

@pytest.mark.slow
def test_long_running_test():
    ...

@pytest.mark.expensive
def test_llm_inference():
    ...

@pytest.mark.llama
def test_requires_llm_model():
    ...
```

Run specific test categories:
```bash
pytest -m unit          # Only unit tests
pytest -m "not slow"    # Skip slow tests
pytest -m "not expensive and not llama and not slow and not integration"  # Fast tests only (pre-commit default)
pytest -m llama         # Run LLM tests (requires model file)
pytest -m slow          # Run slow tests (audio processing with real analysis)
pytest -m integration   # Run integration tests
```

**Important**:
- **LLM tests** are marked as `expensive` and `llama` and are **excluded by default** in CI and pre-commit. These tests require:
  - `llama-cpp-python` installed
  - A valid LLM model file configured via `LLM_MODEL_PATH`
  - Significant computational resources
- **Audio processing tests** that do real audio analysis (e.g., `test_analyze_articulation_basic`, `test_comprehensive_analysis_success`) are marked as `slow` or `integration` and are **excluded from pre-commit hooks** to keep commit times reasonable (~26+ minutes otherwise). These tests are still run in CI.
- LLM service code is intentionally excluded from coverage requirements due to the expense of running these tests.

### Running LLM Integration Tests

LLM integration tests verify that the LLM can actually use tools correctly. These are **critical for catching tool calling bugs** that mocked tests miss.

#### Why Run LLM Tests?

- **Tool calling verification**: Tests verify the LLM can actually call MCP tools (metronome, recording, etc.)
- **Real integration**: Tests use real LLM, real MCP server, and real tool schemas
- **Bug detection**: Catches issues that mocked tests can't (e.g., tool schema format problems, LLM not calling tools)

#### Prerequisites

1. **Install llama-cpp-python**:
   ```bash
   pip install llama-cpp-python
   ```

2. **Download a model file**:
   ```bash
   python scripts/download_model.py llama-3.1-8b-instruct-q4 -o models/
   ```

3. **Configure model path** (via environment variable or `.env`):
   ```bash
   export LLM_MODEL_PATH=models/llama-3.1-8b-instruct-q4.gguf
   ```

#### How to Run

```bash
# Run all LLM tests
pytest -m llama -v

# Run only tool calling tests
pytest tests/integration/test_llm_tool_calling.py -v

# Run only basic LLM tests
pytest tests/integration/test_llm_integration.py -v

# Run with verbose output to see what's happening
pytest -m llama -vv

# Run specific test
pytest tests/integration/test_llm_tool_calling.py::TestLLMToolCallingIntegration::test_llm_can_call_metronome_tool -v
```

#### When to Run LLM Tests

Run these tests:
- **Before releases**: Ensure tool calling works correctly
- **When debugging tool issues**: If tools aren't working in the app, these tests help isolate the problem
- **After LLM-related changes**: After modifying tool schemas, LLM service, or tool calling logic
- **Periodically**: Run manually to catch regressions (they're too expensive for CI)

#### What These Tests Cover

**`test_llm_integration.py`**:
- LLM initialization with real model
- Basic response generation

**`test_llm_tool_calling.py`** (most important):
- LLM can call metronome tool when requested
- LLM can call recording tool when requested
- Tool schemas are properly formatted for the LLM
- Tool calling loop works correctly
- Error handling doesn't crash

#### Troubleshooting

**Tests skip with "LLM not initialized"**:
- Check `LLM_MODEL_PATH` is set correctly
- Verify model file exists at the specified path
- Check model file is valid (not corrupted)

**Tests are slow**:
- This is expected - LLM inference is computationally expensive
- Tests typically take 10-30 seconds each
- Consider running specific tests instead of all at once

**Tool calling tests fail**:
- Check tool schemas are correctly formatted
- Verify MCP server is working (`pytest tests/integration/test_mcp_tool_calling.py`)
- Check LLM model supports function calling (Llama 3.1+ recommended)

### Coverage Requirements

- **Minimum coverage**: 80% (for fast tests in pre-commit)
- **Target coverage**: 90%+
- Coverage reports generated in `htmlcov/` directory

**Note**: Some audio analysis modules (`articulation.py`, `chords.py`, `comprehensive.py`, `dynamics.py`, `groove.py`, `key.py`, `timbre.py`) are excluded from coverage requirements because they are only tested by slow tests that do real audio processing. These tests are excluded from pre-commit hooks to keep commit times reasonable (~26+ minutes otherwise). These modules are still tested in CI and can be run manually with `pytest -m slow`.

View coverage report:
```bash
make test-cov
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Code Style

### Formatting

- **Black**: Automatic code formatting (line length: 100)
- **Ruff**: Fast linting with auto-fix

Format code:
```bash
make format
```

### Type Hints

Use type hints for all functions:

```python
from typing import Dict, List, Optional

def process_audio(audio_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ...
```

### Import Organization

Imports should be organized as:
1. Standard library
2. Third-party packages
3. Local application imports

Ruff's isort handles this automatically.

## Continuous Integration

CI runs on every push and PR:

- Linting (ruff)
- Formatting check (black)
- Type checking (mypy)
- Tests with coverage (pytest)
- Multiple Python versions (3.11, 3.12)

## Common Tasks

### Adding a New Dependency

1. Add to `pyproject.toml` under `[project.dependencies]` or `[project.optional-dependencies.dev]`
2. Install: `pip install -e ".[dev]"`
3. Update lock files if using pip-tools: `make requirements.txt`

### Adding a New Test

1. Create test file in `tests/unit/` or `tests/integration/`
2. Write test following TDD principles
3. Run: `pytest tests/unit/test_new_feature.py`
4. Ensure coverage stays above 80%

### Debugging Tests

```bash
# Run with debug output
pytest -vvs

# Run with pdb on failure
pytest --pdb

# Run specific test with pdb
pytest tests/unit/test_config.py::test_settings_defaults --pdb
```

### Debugging Tool Calls

To see detailed logging for all tool calls (useful for debugging tool invocation issues):

**Via environment variable:**
```bash
export DEBUG_TOOL_CALLS=true
python run.py
```

**Via .env file:**
```
DEBUG_TOOL_CALLS=true
```

When enabled, you'll see detailed logs for:
- Every tool call with its name, ID, and arguments
- Tool results (success or error)
- Widget tools that are returned to the frontend
- MCP server tool invocations

Example output:
```
[TOOL CALL] request_audio_recording
  Tool ID: call_abc123
  Arguments: {
    "prompt": "Please record audio",
    "max_duration": 30.0
  }
[WIDGET TOOL] Returning request_audio_recording to frontend
```

## Project Structure

```
zikos/
├── backend/
│   └── zikos/          # Python backend code
├── frontend/           # TypeScript/HTML frontend
│   ├── src/            # TypeScript source
│   └── dist/           # Compiled output
├── tests/              # Test code
├── .github/workflows/  # CI/CD
├── Makefile           # Common tasks
├── pyproject.toml     # Project config
└── .pre-commit-config.yaml  # Pre-commit hooks
```

## Best Practices

1. **Write tests first** (TDD)
2. **Run checks before committing** (`make check`)
3. **Keep coverage high** (80%+)
4. **Use type hints** everywhere
5. **Follow Black formatting** (auto-formatted)
6. **Write docstrings** for all public functions/classes
7. **Keep functions small** and focused
8. **Use meaningful names** for variables and functions

## Troubleshooting

### Tests failing?

```bash
# Clear pytest cache
rm -rf .pytest_cache

# Reinstall dependencies
pip install -e ".[dev]"
```

### Type checking errors?

```bash
# Check specific file
mypy backend/zikos/config.py

# Ignore missing imports (for external packages)
# Already configured in pyproject.toml
```

### Coverage too low?

```bash
# See what's not covered
pytest --cov=backend/zikos --cov-report=term-missing

# Focus on uncovered lines
```
