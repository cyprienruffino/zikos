"""Unit tests for WebSocket streaming endpoint"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect

from zikos.api.chat import get_chat_service, websocket_endpoint


@pytest.fixture
def mock_websocket():
    """Mock WebSocket"""
    ws = MagicMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_chat_service():
    """Mock ChatService with streaming support"""
    service = MagicMock()

    async def mock_process_message_stream(message, session_id):
        yield {"type": "session_id", "session_id": session_id or "test_session"}
        yield {"type": "token", "content": "Hello"}
        yield {"type": "token", "content": " there"}
        yield {"type": "response", "message": "Hello there"}

    service.process_message_stream = mock_process_message_stream
    service.process_message = AsyncMock(return_value={"type": "response", "message": "Test"})
    service.handle_audio_ready = AsyncMock(
        return_value={"type": "response", "message": "Audio processed"}
    )
    service.get_thinking = MagicMock(return_value={"thinking": []})
    service.disconnect = AsyncMock()

    return service


class TestWebSocketStreaming:
    """Tests for WebSocket streaming functionality"""

    @pytest.mark.asyncio
    async def test_websocket_streaming_message(self, mock_websocket, mock_chat_service):
        """Test WebSocket handles streaming messages"""
        with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
            call_count = 0

            async def receive_json():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {
                        "type": "message",
                        "message": "Hello",
                        "stream": True,
                        "session_id": "test_session",
                    }
                else:
                    raise StopAsyncIteration()

            mock_websocket.receive_json = receive_json

            try:
                await websocket_endpoint(mock_websocket)
            except (StopAsyncIteration, RuntimeError):
                pass

            mock_websocket.accept.assert_called_once()
            # Should have sent multiple chunks for streaming
            assert mock_websocket.send_json.call_count >= 3

    @pytest.mark.asyncio
    async def test_websocket_non_streaming_message(self, mock_websocket, mock_chat_service):
        """Test WebSocket handles non-streaming messages"""
        with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
            call_count = 0

            async def receive_json():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"type": "message", "message": "Hello", "stream": False}
                else:
                    raise WebSocketDisconnect()

            mock_websocket.receive_json = receive_json

            try:
                await websocket_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass

            mock_websocket.accept.assert_called_once()
            # Should have sent response (may also send error on disconnect)
            assert mock_websocket.send_json.call_count >= 1
            mock_chat_service.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_streaming_error_handling(self, mock_websocket, mock_chat_service):
        """Test WebSocket handles streaming errors"""

        async def failing_stream(*args, **kwargs):
            yield {"type": "token", "content": "Hello"}
            raise RuntimeError("Streaming error")

        mock_chat_service.process_message_stream = failing_stream

        with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
            call_count = 0

            async def receive_json():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"type": "message", "message": "Hello", "stream": True}
                else:
                    raise StopAsyncIteration()

            mock_websocket.receive_json = receive_json

            try:
                await websocket_endpoint(mock_websocket)
            except (StopAsyncIteration, RuntimeError):
                pass

            # Should have sent at least one chunk before error
            assert mock_websocket.send_json.call_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_streaming_with_session_id(self, mock_websocket, mock_chat_service):
        """Test WebSocket streaming preserves session ID"""
        captured_session_id = None

        async def mock_process_message_stream(message, session_id):
            nonlocal captured_session_id
            captured_session_id = session_id
            yield {"type": "session_id", "session_id": session_id}
            yield {"type": "token", "content": "Hello"}
            yield {"type": "response", "message": "Hello"}

        mock_chat_service.process_message_stream = mock_process_message_stream

        with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):
            call_count = 0

            async def receive_json():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {
                        "type": "message",
                        "message": "Hello",
                        "stream": True,
                        "session_id": "custom_session",
                    }
                else:
                    raise WebSocketDisconnect()

            mock_websocket.receive_json = receive_json

            try:
                await websocket_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass

            # Verify session_id was passed to service
            assert captured_session_id == "custom_session"

    @pytest.mark.asyncio
    async def test_websocket_streaming_disconnect(self, mock_websocket, mock_chat_service):
        """Test WebSocket handles disconnect during streaming"""
        with patch("zikos.api.chat.get_chat_service", return_value=mock_chat_service):

            async def receive_json():
                raise WebSocketDisconnect()

            mock_websocket.receive_json = receive_json

            try:
                await websocket_endpoint(mock_websocket)
            except WebSocketDisconnect:
                pass

            mock_chat_service.disconnect.assert_called_once_with(mock_websocket)
