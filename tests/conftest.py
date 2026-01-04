"""Pytest configuration and fixtures"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def storage_paths(temp_dir, monkeypatch):
    """Configure storage paths to use temporary directory for tests

    This fixture sets environment variables and patches the settings object
    and service instances to ensure all file operations use the temporary
    directory, which is automatically cleaned up after each test.
    """
    from zikos.config import settings

    temp_dir_str = str(temp_dir)

    monkeypatch.setenv("AUDIO_STORAGE_PATH", temp_dir_str)
    monkeypatch.setenv("MIDI_STORAGE_PATH", temp_dir_str)
    monkeypatch.setenv("NOTATION_STORAGE_PATH", temp_dir_str)

    patches = [
        patch.object(settings, "audio_storage_path", temp_dir),
        patch.object(settings, "midi_storage_path", temp_dir),
        patch.object(settings, "notation_storage_path", temp_dir),
    ]

    try:
        from zikos.api.audio import audio_service
        from zikos.api.midi import midi_service

        patches.extend(
            [
                patch.object(audio_service, "storage_path", temp_dir),
                patch.object(midi_service, "storage_path", temp_dir),
                patch.object(midi_service, "notation_path", temp_dir),
                patch.object(midi_service.midi_tools, "storage_path", temp_dir),
            ]
        )
    except ImportError:
        pass

    from contextlib import ExitStack

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield temp_dir


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
