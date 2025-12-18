"""Pytest configuration and fixtures"""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_audio_path(temp_dir):
    """Create sample audio file path"""
    return temp_dir / "sample.wav"


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    from unittest.mock import MagicMock

    llm = MagicMock()
    llm.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Test response"}}]
    }
    return llm
