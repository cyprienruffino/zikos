"""Tests for main application"""

import pytest
from fastapi.testclient import TestClient

from src.zikos.main import app


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
