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
```

Run specific test categories:
```bash
pytest -m unit          # Only unit tests
pytest -m "not slow"    # Skip slow tests
```

### Coverage Requirements

- **Minimum coverage**: 80%
- **Target coverage**: 90%+
- Coverage reports generated in `htmlcov/` directory

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

## Project Structure

```
zikos/
├── src/zikos/          # Source code
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
mypy src/zikos/config.py

# Ignore missing imports (for external packages)
# Already configured in pyproject.toml
```

### Coverage too low?

```bash
# See what's not covered
pytest --cov=src/zikos --cov-report=term-missing

# Focus on uncovered lines
```

