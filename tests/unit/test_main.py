"""Tests for main application"""

import pytest
from fastapi.testclient import TestClient

from zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestMain:
    """Tests for main application"""

    def test_app_creation(self):
        """Test that app is created"""
        assert app is not None
        assert app.title == "Zikos - AI Music Teacher"

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint(self, client):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_root_endpoint_no_index(self, client):
        """Test root endpoint when index.html doesn't exist"""
        from pathlib import Path
        from unittest.mock import patch

        with patch("zikos.main.frontend_dir") as mock_frontend_dir:
            mock_index_path = mock_frontend_dir / "index.html"
            mock_index_path.exists.return_value = False

            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"] == "Zikos API"
            assert "version" in data
