"""Configuration management"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from zikos.constants import LLMConstants

_logger = logging.getLogger(__name__)

load_dotenv()


class Settings(BaseModel):
    """Application settings"""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # LLM — local backends
    llm_model_path: str = ""
    llm_backend: str = "auto"
    llm_tool_format: str = "auto"  # auto, qwen, simplified, native
    llm_n_ctx: int | None = None
    llm_n_gpu_layers: int = LLMConstants.DEFAULT_N_GPU_LAYERS
    llm_temperature: float = LLMConstants.DEFAULT_TEMPERATURE
    llm_top_p: float = LLMConstants.DEFAULT_TOP_P
    llm_top_k: int = LLMConstants.DEFAULT_TOP_K
    llm_max_thinking_tokens: int = LLMConstants.DEFAULT_MAX_THINKING_TOKENS

    # LLM — cloud backends (used when LLM_PROVIDER is set)
    llm_provider: str = ""  # openai | anthropic | gemini | mistral | ...
    llm_api_key: str = ""  # forwarded to litellm; alternatively set provider-specific env var
    llm_model_name: str = ""  # litellm model string, e.g. gpt-4o, gemini/gemini-2.0-flash

    # Storage
    audio_storage_path: Path = Path("audio_storage")
    midi_storage_path: Path = Path("midi_storage")
    notation_storage_path: Path = Path("notation_storage")
    soundfont_path: str = ""  # Path to .sf2 file for FluidSynth synthesis

    # MCP
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 8001

    # User settings
    user_settings_path: Path = Path("data/user_settings.json")

    # Debug
    debug_tool_calls: bool = False

    @staticmethod
    def _parse_optional_int(env_var: str) -> int | None:
        raw = os.getenv(env_var)
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            _logger.warning(f"Invalid value for {env_var}: {raw!r}, ignoring")
            return None

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables

        Uses class field defaults, so defaults are defined in one place.
        """
        defaults = cls()
        return cls(
            api_host=os.getenv("API_HOST", defaults.api_host),
            api_port=int(os.getenv("API_PORT", str(defaults.api_port))),
            api_reload=os.getenv("API_RELOAD", str(defaults.api_reload).lower()).lower() == "true",
            llm_model_path=os.getenv("LLM_MODEL_PATH", defaults.llm_model_path),
            llm_backend=os.getenv("LLM_BACKEND", defaults.llm_backend),
            llm_tool_format=os.getenv("LLM_TOOL_FORMAT", defaults.llm_tool_format),
            llm_n_ctx=cls._parse_optional_int("LLM_N_CTX"),
            llm_n_gpu_layers=int(os.getenv("LLM_N_GPU_LAYERS", str(defaults.llm_n_gpu_layers))),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", str(defaults.llm_temperature))),
            llm_top_p=float(os.getenv("LLM_TOP_P", str(defaults.llm_top_p))),
            llm_top_k=int(os.getenv("LLM_TOP_K", str(defaults.llm_top_k))),
            llm_max_thinking_tokens=int(
                os.getenv("LLM_MAX_THINKING_TOKENS", str(defaults.llm_max_thinking_tokens))
            ),
            audio_storage_path=Path(
                os.getenv("AUDIO_STORAGE_PATH", str(defaults.audio_storage_path))
            ),
            midi_storage_path=Path(os.getenv("MIDI_STORAGE_PATH", str(defaults.midi_storage_path))),
            notation_storage_path=Path(
                os.getenv("NOTATION_STORAGE_PATH", str(defaults.notation_storage_path))
            ),
            mcp_server_host=os.getenv("MCP_SERVER_HOST", defaults.mcp_server_host),
            mcp_server_port=int(os.getenv("MCP_SERVER_PORT", str(defaults.mcp_server_port))),
            user_settings_path=Path(
                os.getenv("USER_SETTINGS_PATH", str(defaults.user_settings_path))
            ),
            debug_tool_calls=os.getenv(
                "DEBUG_TOOL_CALLS", str(defaults.debug_tool_calls).lower()
            ).lower()
            == "true",
            soundfont_path=os.getenv("SOUNDFONT_PATH", defaults.soundfont_path),
            llm_provider=os.getenv("LLM_PROVIDER", defaults.llm_provider),
            llm_api_key=os.getenv("LLM_API_KEY", defaults.llm_api_key),
            llm_model_name=os.getenv("LLM_MODEL_NAME", defaults.llm_model_name),
        )


settings = Settings.from_env()
