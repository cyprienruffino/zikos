#!/usr/bin/env python3
"""Run the application"""

import uvicorn

from src.zikos.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.zikos.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
