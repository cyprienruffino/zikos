"""FastAPI application entry point"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
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


class NoCacheStaticFiles(StaticFiles):
    """StaticFiles with no-cache headers and query parameter stripping"""

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            if "?" in path:
                scope = dict(scope)
                scope["path"] = path.split("?")[0]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"cache-control"] = b"no-cache, no-store, must-revalidate"
                headers[b"pragma"] = b"no-cache"
                headers[b"expires"] = b"0"
                message["headers"] = list(headers.items())
            await send(message)

        await super().__call__(scope, receive, send_wrapper)


if dist_dir.exists():
    static_files = NoCacheStaticFiles(directory=str(dist_dir))
    app.mount("/static", static_files, name="static")


@app.get("/")
async def root():
    """Serve the frontend UI"""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        response = FileResponse(index_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return {"message": "Zikos API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
