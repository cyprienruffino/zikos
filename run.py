#!/usr/bin/env python3
"""Run the application"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

import uvicorn  # noqa: E402

from zikos.config import settings  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "zikos.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
