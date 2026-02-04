"""System API endpoints for hardware detection and model recommendations"""

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from zikos.utils.gpu import detect_hardware
from zikos.utils.model_recommendations import (
    get_default_model_path,
    get_hardware_tier,
    get_recommended_models,
)

router = APIRouter()


class GpuInfoResponse(BaseModel):
    available: bool
    device: int | None = None
    name: str | None = None
    memory_total_gb: float | None = None
    memory_free_gb: float | None = None


class RamInfoResponse(BaseModel):
    total_gb: float
    available_gb: float


class GpuHintResponse(BaseModel):
    hint_type: str
    message: str
    docs_url: str


class HardwareResponse(BaseModel):
    gpu: GpuInfoResponse
    ram: RamInfoResponse
    gpu_hint: GpuHintResponse | None = None
    tier: str


class ModelRecommendationResponse(BaseModel):
    name: str
    filename: str
    size_gb: float
    vram_required_gb: float
    ram_required_gb: float
    context_window: int
    download_url: str
    description: str
    tier: str


class ModelRecommendationsResponse(BaseModel):
    default_model_path: str
    primary_recommendation: ModelRecommendationResponse | None
    all_recommendations: list[ModelRecommendationResponse]


class SystemStatusResponse(BaseModel):
    model_loaded: bool
    model_path: str | None = None
    initialization_error: str | None = None
    hardware: HardwareResponse


@router.get("/hardware", response_model=HardwareResponse)
async def get_hardware():
    """Get detected hardware profile"""
    profile = detect_hardware()
    tier = get_hardware_tier(profile)

    return HardwareResponse(
        gpu=GpuInfoResponse(**asdict(profile.gpu)),
        ram=RamInfoResponse(**asdict(profile.ram)),
        gpu_hint=GpuHintResponse(**asdict(profile.gpu_hint)) if profile.gpu_hint else None,
        tier=tier,
    )


@router.get("/model-recommendations", response_model=ModelRecommendationsResponse)
async def get_model_recommendations():
    """Get model recommendations based on detected hardware"""
    profile = detect_hardware()
    recommendations = get_recommended_models(profile)

    return ModelRecommendationsResponse(
        default_model_path=get_default_model_path(),
        primary_recommendation=(
            ModelRecommendationResponse(**asdict(recommendations[0])) if recommendations else None
        ),
        all_recommendations=[ModelRecommendationResponse(**asdict(r)) for r in recommendations],
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_status():
    """Get system status including model state and hardware info"""
    from zikos.api.chat import get_chat_service
    from zikos.config import Settings

    settings = Settings()
    profile = detect_hardware()
    tier = get_hardware_tier(profile)

    chat_service = get_chat_service()
    llm_service = chat_service.llm_service

    model_loaded = llm_service.backend is not None
    initialization_error = llm_service.initialization_error

    return SystemStatusResponse(
        model_loaded=model_loaded,
        model_path=settings.llm_model_path if settings.llm_model_path else None,
        initialization_error=initialization_error,
        hardware=HardwareResponse(
            gpu=GpuInfoResponse(**asdict(profile.gpu)),
            ram=RamInfoResponse(**asdict(profile.ram)),
            gpu_hint=GpuHintResponse(**asdict(profile.gpu_hint)) if profile.gpu_hint else None,
            tier=tier,
        ),
    )
