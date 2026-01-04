# Development Quick Reference

## Setup

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
make install-dev
pre-commit install
```

## Commands

### Testing
- `make test-cov` - All tests with coverage
- `make test-fast` - Tests without coverage (faster)
- `pytest tests/unit/test_config.py` - Specific test file
- `pytest -k "test_config"` - Tests matching pattern
- `pytest -n auto` - Parallel execution
- `pytest -m comprehensive` - Comprehensive tests (LLM, heavy audio)
- `pytest -m integration` - Integration tests
- `pytest -m "not comprehensive and not integration"` - Fast tests only (pre-commit default)

### Code Quality
- `make check` - All checks (lint + format-check + type-check)
- `make lint` - Run ruff linter
- `make format-check` - Check formatting
- `make format` - Auto-format code
- `make type-check` - Run mypy

### Pre-commit
- `pre-commit run --all-files` - Run hooks manually
- Hooks run: trailing whitespace, EOF fixes, YAML/JSON/TOML validation, Black, Ruff, MyPy, fast unit tests only

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── unit/               # Unit tests (fast, isolated)
├── integration/        # Integration tests (slower, test interactions)
└── comprehensive/      # Comprehensive tests (LLM, heavy audio processing)
```

## Test Markers

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.comprehensive` - Requires LLM model, heavy audio processing, or long runtime

**Important**: Comprehensive and integration tests are excluded from pre-commit hooks (default pytest config excludes both). Pre-commit uses 75% coverage threshold (vs 80% for main pytest).

## LLM Integration Tests

### Prerequisites
1. Install llama-cpp-python: `pip install llama-cpp-python`
2. Download model: `python scripts/download_model.py llama-3.1-8b-instruct-q4 -o models/`
3. Set `LLM_MODEL_PATH` environment variable

### Run
- `pytest -m comprehensive -v` - All comprehensive tests
- `pytest tests/integration/test_llm_tool_calling.py -v` - LLM tool calling tests
- `pytest tests/integration/test_llm_integration.py -v` - Basic LLM tests

### When to Run
- Before releases
- When debugging tool issues
- After LLM-related changes
- Periodically to catch regressions

## Coverage

- **Minimum**: 80% (pytest default)
- **Pre-commit threshold**: 75% (lower to account for excluded tests)
- **Target**: 90%+

### Excluded from Coverage
- `services/llm.py` - Requires real LLM models
- `llm_backends/*` - Require real models, integration-tested
- `utils/gpu.py` - Environment-specific

**Note**: Audio analysis modules (articulation, chords, dynamics, groove, key, timbre, time_stretch) are included in coverage (tested with real librosa on synthetic audio).

## Code Style

- **Black**: Auto-formatting (line length: 100)
- **Ruff**: Fast linting with auto-fix
- **Type hints**: Required for all functions
- **Import organization**: Standard library → third-party → local (handled by ruff isort)

## Debugging

### Tool Calls
Set `DEBUG_TOOL_CALLS=true` in environment or `.env` file for verbose tool calling logs.

### Tests
- `pytest -vvs` - Verbose output
- `pytest --pdb` - Drop into debugger on failure
- `pytest tests/unit/test_config.py::test_settings_defaults --pdb` - Specific test with pdb

## Project Structure

```
zikos/
├── backend/zikos/      # Python backend code
├── frontend/           # TypeScript/HTML frontend
│   ├── src/            # TypeScript source
│   └── dist/           # Compiled output
├── tests/              # Test code
├── .github/workflows/  # CI/CD
├── Makefile           # Common tasks
├── pyproject.toml     # Project config
└── .pre-commit-config.yaml  # Pre-commit hooks
```

## Common Tasks

### Adding Dependency
1. Add to `pyproject.toml` under `[project.dependencies]` or `[project.optional-dependencies.dev]`
2. Install: `pip install -e ".[dev]"`
3. Update lock files if using pip-tools: `make requirements.txt`

### Adding Test
1. Create test file in `tests/unit/` or `tests/integration/`
2. Write test following TDD principles
3. Run: `pytest tests/unit/test_new_feature.py`
4. Ensure coverage stays above 80%

### Troubleshooting

**Tests failing?**
```bash
rm -rf .pytest_cache
pip install -e ".[dev]"
```

**Type checking errors?**
```bash
mypy backend/zikos/config.py
```

**Coverage too low?**
```bash
pytest --cov=backend/zikos --cov-report=term-missing
```
