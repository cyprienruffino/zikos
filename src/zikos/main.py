"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.zikos.api import router

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


@app.get("/")
async def root():
    return {"message": "Zikos API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
