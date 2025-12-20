"""Tests for configuration"""

import os

import pytest

from zikos.config import Settings


@pytest.mark.lightweight
def test_settings_defaults():
    """Test default settings"""
    # Temporarily remove API_RELOAD from environment to test defaults
    api_reload_value = os.environ.pop("API_RELOAD", None)
    try:
        settings = Settings.from_env()
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.api_reload is False
    finally:
        # Restore original value if it existed
        if api_reload_value is not None:
            os.environ["API_RELOAD"] = api_reload_value


@pytest.mark.lightweight
def test_settings_from_env():
    """Test settings from environment variables"""
    os.environ["API_PORT"] = "9000"
    os.environ["LLM_TEMPERATURE"] = "0.5"

    settings = Settings.from_env()
    assert settings.api_port == 9000
    assert settings.llm_temperature == 0.5

    # Cleanup
    del os.environ["API_PORT"]
    del os.environ["LLM_TEMPERATURE"]
