"""Unit tests for debug API endpoints (DEBUG_API_TOKEN gating)"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from zikos.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Mock chat service with a conversation manager"""
    service = MagicMock()
    service.llm_service.conversation_manager.conversations = {"sess-1": []}
    return service


class TestDebugTokenGating:
    def test_endpoints_404_when_token_unset(self, client):
        with patch("zikos.api.debug.settings") as mock_settings:
            mock_settings.debug_api_token = ""
            assert client.get("/api/debug/sessions").status_code == 404
            assert client.get("/api/debug/session/sess-1").status_code == 404

    def test_endpoints_403_without_header_when_token_set(self, client):
        with patch("zikos.api.debug.settings") as mock_settings:
            mock_settings.debug_api_token = "s3cret"
            assert client.get("/api/debug/sessions").status_code == 403

    def test_endpoints_403_with_wrong_token(self, client):
        with patch("zikos.api.debug.settings") as mock_settings:
            mock_settings.debug_api_token = "s3cret"
            response = client.get("/api/debug/sessions", headers={"X-Debug-Token": "wrong"})
            assert response.status_code == 403

    def test_endpoints_ok_with_correct_token(self, client, mock_chat_service):
        with patch("zikos.api.debug.settings") as mock_settings:
            mock_settings.debug_api_token = "s3cret"
            with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
                response = client.get(
                    "/api/debug/sessions", headers={"X-Debug-Token": "s3cret"}
                )
        assert response.status_code == 200
        assert response.json() == {"sessions": ["sess-1"]}

    def test_session_dump_ok_with_correct_token(self, client, mock_chat_service):
        with patch("zikos.api.debug.settings") as mock_settings:
            mock_settings.debug_api_token = "s3cret"
            with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
                response = client.get(
                    "/api/debug/session/sess-1", headers={"X-Debug-Token": "s3cret"}
                )
        assert response.status_code == 200
        assert response.json()["session_id"] == "sess-1"
