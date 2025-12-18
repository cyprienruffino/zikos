"""Integration tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient

from src.zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    # Root endpoint serves HTML if index.html exists, otherwise JSON
    if response.headers.get("content-type", "").startswith("text/html"):
        assert b"<!doctype html>" in response.content or b"<html" in response.content
    else:
        assert "message" in response.json()


def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
