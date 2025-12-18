.PHONY: help install install-dev test test-cov lint format type-check check clean run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -e .

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests (excludes expensive/slow tests)
	pytest

test-cov: ## Run tests with coverage (excludes expensive/slow tests)
	pytest --cov=src/zikos --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without coverage (faster, excludes expensive/slow tests)
	pytest --no-cov -x

test-all: ## Run all tests including expensive ones
	pytest -m ""

test-expensive: ## Run only expensive tests (LLM, etc.)
	pytest -m "expensive or llama"

test-slow: ## Run slow tests
	pytest -m "slow"

lint: ## Run linters (ruff + eslint)
	ruff check src tests
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run lint; fi

lint-js: ## Run TypeScript linter (eslint)
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run lint; else echo "npm not found or package.json missing, skipping TS lint"; fi

build-js: ## Build TypeScript to JavaScript
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run build; else echo "npm not found or package.json missing, skipping TS build"; fi

type-check-js: ## Run TypeScript type checker
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run type-check; else echo "npm not found or package.json missing, skipping TS type check"; fi

test-js: ## Run TypeScript tests
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run test; else echo "npm not found or package.json missing, skipping TS tests"; fi

format-check: ## Check code formatting (black + prettier)
	black --check src tests
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run format:check; fi

format: ## Format code (black + prettier)
	black src tests
	ruff check --fix src tests
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run format; fi

format-js: ## Format TypeScript code (prettier)
	@if command -v npm >/dev/null 2>&1 && [ -f package.json ]; then npm run format; else echo "npm not found or package.json missing, skipping TS format"; fi

type-check: ## Run type checker (mypy)
	mypy src

check: lint format-check type-check ## Run all checks

clean: ## Clean build artifacts
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov .mypy_cache
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run: ## Run the application
	python run.py

download-model: ## Download Llama model (usage: make download-model MODEL=llama-3.1-8b-instruct-q4)
	@if [ -z "$(MODEL)" ]; then \
		python scripts/download_model.py --list; \
		echo ""; \
		echo "Usage: make download-model MODEL=<model-name>"; \
		echo "Example: make download-model MODEL=llama-3.1-8b-instruct-q4"; \
	else \
		python scripts/download_model.py $(MODEL); \
	fi

requirements.txt: pyproject.toml ## Generate requirements.txt from pyproject.toml
	pip-compile pyproject.toml -o requirements.txt

requirements-dev.txt: pyproject.toml ## Generate requirements-dev.txt
	pip-compile pyproject.toml --extra=dev -o requirements-dev.txt
