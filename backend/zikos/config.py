"""Configuration management"""

import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings"""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # LLM
    llm_model_path: str = ""
    llm_n_ctx: int = 4096
    llm_n_gpu_layers: int = 0
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9

    # Storage
    audio_storage_path: Path = Path("audio_storage")
    midi_storage_path: Path = Path("midi_storage")
    notation_storage_path: Path = Path("notation_storage")

    # MCP
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 8001

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        return cls(
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            api_reload=os.getenv("API_RELOAD", "false").lower() == "true",
            llm_model_path=os.getenv("LLM_MODEL_PATH", ""),
            llm_n_ctx=int(os.getenv("LLM_N_CTX", "4096")),
            llm_n_gpu_layers=int(os.getenv("LLM_N_GPU_LAYERS", "0")),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            llm_top_p=float(os.getenv("LLM_TOP_P", "0.9")),
            audio_storage_path=Path(os.getenv("AUDIO_STORAGE_PATH", "audio_storage")),
            midi_storage_path=Path(os.getenv("MIDI_STORAGE_PATH", "midi_storage")),
            notation_storage_path=Path(os.getenv("NOTATION_STORAGE_PATH", "notation_storage")),
            mcp_server_host=os.getenv("MCP_SERVER_HOST", "localhost"),
            mcp_server_port=int(os.getenv("MCP_SERVER_PORT", "8001")),
        )


settings = Settings.from_env()
