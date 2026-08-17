"""Tests for configuration"""

import os

import pytest

from zikos.config import Settings


@pytest.mark.lightweight
def test_settings_defaults():
    """Test default settings"""
    # Temporarily remove relevant vars from environment to test defaults
    saved = {var: os.environ.pop(var, None) for var in ("API_RELOAD", "API_HOST", "CORS_ORIGINS")}
    try:
        settings = Settings.from_env()
        # Default bind is loopback, not 0.0.0.0 (docker-compose overrides via API_HOST)
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8000
        assert settings.api_reload is False
        assert settings.cors_origins == [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    finally:
        # Restore original values if they existed
        for var, value in saved.items():
            if value is not None:
                os.environ[var] = value


@pytest.mark.lightweight
def test_cors_origins_from_env():
    """CORS origins are parsed from a comma-separated env var"""
    os.environ["CORS_ORIGINS"] = "http://example.com, https://app.example.com"
    try:
        settings = Settings.from_env()
        assert settings.cors_origins == ["http://example.com", "https://app.example.com"]
    finally:
        del os.environ["CORS_ORIGINS"]


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
