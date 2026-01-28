"""Integration tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient

from zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns frontend HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert b"<!doctype html>" in response.content.lower() or b"<!DOCTYPE html>" in response.content


def test_health_endpoint(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
