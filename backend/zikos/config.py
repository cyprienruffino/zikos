"""Configuration management"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from zikos.constants import LLMConstants

load_dotenv()


class Settings(BaseModel):
    """Application settings"""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # LLM
    llm_model_path: str = ""
    llm_backend: str = "auto"
    llm_n_ctx: int = LLMConstants.DEFAULT_N_CTX
    llm_n_gpu_layers: int = LLMConstants.DEFAULT_N_GPU_LAYERS
    llm_temperature: float = LLMConstants.DEFAULT_TEMPERATURE
    llm_top_p: float = LLMConstants.DEFAULT_TOP_P

    # Storage
    audio_storage_path: Path = Path("audio_storage")
    midi_storage_path: Path = Path("midi_storage")
    notation_storage_path: Path = Path("notation_storage")

    # MCP
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 8001

    # Music Flamingo Service
    music_flamingo_service_url: str = ""

    # Debug
    debug_tool_calls: bool = False

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
            llm_n_ctx=int(os.getenv("LLM_N_CTX", str(defaults.llm_n_ctx))),
            llm_n_gpu_layers=int(os.getenv("LLM_N_GPU_LAYERS", str(defaults.llm_n_gpu_layers))),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", str(defaults.llm_temperature))),
            llm_top_p=float(os.getenv("LLM_TOP_P", str(defaults.llm_top_p))),
            audio_storage_path=Path(
                os.getenv("AUDIO_STORAGE_PATH", str(defaults.audio_storage_path))
            ),
            midi_storage_path=Path(os.getenv("MIDI_STORAGE_PATH", str(defaults.midi_storage_path))),
            notation_storage_path=Path(
                os.getenv("NOTATION_STORAGE_PATH", str(defaults.notation_storage_path))
            ),
            mcp_server_host=os.getenv("MCP_SERVER_HOST", defaults.mcp_server_host),
            mcp_server_port=int(os.getenv("MCP_SERVER_PORT", str(defaults.mcp_server_port))),
            music_flamingo_service_url=os.getenv(
                "MUSIC_FLAMINGO_SERVICE_URL", defaults.music_flamingo_service_url
            ),
            debug_tool_calls=os.getenv(
                "DEBUG_TOOL_CALLS", str(defaults.debug_tool_calls).lower()
            ).lower()
            == "true",
        )


settings = Settings.from_env()
