"""Unit tests for system API endpoints"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from zikos.api.system import router
from zikos.main import app
from zikos.utils.gpu import GpuHint, GpuInfo, HardwareProfile, RamInfo
from zikos.utils.model_recommendations import ModelRecommendation

app.include_router(router, prefix="/api/system")


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_hardware_profile():
    """Create a mock hardware profile"""
    return HardwareProfile(
        gpu=GpuInfo(
            available=True,
            device=0,
            name="NVIDIA GeForce RTX 3080",
            memory_total_gb=10.0,
            memory_free_gb=8.0,
        ),
        ram=RamInfo(total_gb=32.0, available_gb=24.0),
        gpu_hint=None,
    )


@pytest.fixture
def mock_hardware_profile_no_gpu():
    """Create a mock hardware profile without GPU"""
    return HardwareProfile(
        gpu=GpuInfo(available=False),
        ram=RamInfo(total_gb=16.0, available_gb=12.0),
        gpu_hint=GpuHint(
            hint_type="no_gpu_detected",
            message="No GPU detected",
            docs_url="https://docs.nvidia.com/cuda/",
        ),
    )


@pytest.fixture
def mock_model_recommendations():
    """Create mock model recommendations"""
    return [
        ModelRecommendation(
            name="Qwen3-8B",
            filename="qwen3-8b-q4_k_m.gguf",
            size_gb=5.0,
            vram_required_gb=8.0,
            ram_required_gb=10.0,
            context_window=32768,
            download_url="https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/qwen3-8b-q4_k_m.gguf",
            description="Strong mid-range model",
            tier="medium",
        ),
        ModelRecommendation(
            name="Qwen3-4B",
            filename="qwen3-4b-q4_k_m.gguf",
            size_gb=2.8,
            vram_required_gb=4.0,
            ram_required_gb=6.0,
            context_window=32768,
            download_url="https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/qwen3-4b-q4_k_m.gguf",
            description="Balanced small model",
            tier="low",
        ),
    ]


class TestHardwareEndpoint:
    def test_get_hardware_with_gpu(self, client, mock_hardware_profile):
        """Test hardware endpoint returns GPU info"""
        with patch("zikos.api.system.detect_hardware", return_value=mock_hardware_profile):
            with patch("zikos.api.system.get_hardware_tier", return_value="medium"):
                response = client.get("/api/system/hardware")

        assert response.status_code == 200
        data = response.json()
        assert data["gpu"]["available"] is True
        assert data["gpu"]["name"] == "NVIDIA GeForce RTX 3080"
        assert data["ram"]["total_gb"] == 32.0
        assert data["tier"] == "medium"
        assert data["gpu_hint"] is None

    def test_get_hardware_without_gpu(self, client, mock_hardware_profile_no_gpu):
        """Test hardware endpoint returns hint when no GPU"""
        with patch("zikos.api.system.detect_hardware", return_value=mock_hardware_profile_no_gpu):
            with patch("zikos.api.system.get_hardware_tier", return_value="cpu"):
                response = client.get("/api/system/hardware")

        assert response.status_code == 200
        data = response.json()
        assert data["gpu"]["available"] is False
        assert data["gpu_hint"] is not None
        assert data["gpu_hint"]["hint_type"] == "no_gpu_detected"
        assert "docs_url" in data["gpu_hint"]


class TestModelRecommendationsEndpoint:
    def test_get_recommendations(self, client, mock_hardware_profile, mock_model_recommendations):
        """Test model recommendations endpoint"""
        with patch("zikos.api.system.detect_hardware", return_value=mock_hardware_profile):
            with patch(
                "zikos.api.system.get_recommended_models",
                return_value=mock_model_recommendations,
            ):
                with patch(
                    "zikos.api.system.get_default_model_path",
                    return_value="/home/user/models",
                ):
                    response = client.get("/api/system/model-recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data["default_model_path"] == "/home/user/models"
        assert data["primary_recommendation"]["name"] == "Qwen3-8B"
        assert len(data["all_recommendations"]) == 2
        assert "download_url" in data["all_recommendations"][0]

    def test_get_recommendations_empty(self, client, mock_hardware_profile_no_gpu):
        """Test model recommendations when no models fit"""
        with patch("zikos.api.system.detect_hardware", return_value=mock_hardware_profile_no_gpu):
            with patch("zikos.api.system.get_recommended_models", return_value=[]):
                with patch(
                    "zikos.api.system.get_default_model_path",
                    return_value="/home/user/models",
                ):
                    response = client.get("/api/system/model-recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data["primary_recommendation"] is None
        assert data["all_recommendations"] == []


class TestStatusEndpoint:
    def test_get_status_model_loaded(self, client, mock_hardware_profile):
        """Test status endpoint when model is loaded"""
        mock_llm_service = MagicMock()
        mock_llm_service.backend = MagicMock()
        mock_llm_service.initialization_error = None

        mock_chat_service = MagicMock()
        mock_chat_service.llm_service = mock_llm_service

        mock_settings = MagicMock()
        mock_settings.llm_model_path = "/path/to/model.gguf"

        with patch("zikos.api.system.detect_hardware", return_value=mock_hardware_profile):
            with patch("zikos.api.system.get_hardware_tier", return_value="medium"):
                with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
                    with patch("zikos.config.Settings", return_value=mock_settings):
                        response = client.get("/api/system/status")

        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is True
        assert data["model_path"] == "/path/to/model.gguf"
        assert data["initialization_error"] is None

    def test_get_status_model_not_loaded(self, client, mock_hardware_profile):
        """Test status endpoint when model is not loaded"""
        mock_llm_service = MagicMock()
        mock_llm_service.backend = None
        mock_llm_service.initialization_error = "LLM_MODEL_PATH not set"

        mock_chat_service = MagicMock()
        mock_chat_service.llm_service = mock_llm_service

        mock_settings = MagicMock()
        mock_settings.llm_model_path = ""

        with patch("zikos.api.system.detect_hardware", return_value=mock_hardware_profile):
            with patch("zikos.api.system.get_hardware_tier", return_value="medium"):
                with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
                    with patch("zikos.config.Settings", return_value=mock_settings):
                        response = client.get("/api/system/status")

        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is False
        assert data["model_path"] is None
        assert data["initialization_error"] == "LLM_MODEL_PATH not set"
