"""FastAPI application entry point"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from zikos.api import router

app = FastAPI(
    title="Zikos - AI Music Teacher",
    description="POC for AI-powered music teaching",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

frontend_dir = Path(__file__).parent.parent.parent / "frontend"
dist_dir = frontend_dir / "dist"
if dist_dir.exists():
    app.mount("/static", StaticFiles(directory=str(dist_dir)), name="static")


@app.get("/")
async def root():
    """Serve the frontend UI"""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Zikos API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
