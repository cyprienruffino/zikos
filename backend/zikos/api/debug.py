"""Debug endpoints — only active when DEBUG_API_TOKEN is configured

These endpoints expose full conversation content, so they are hidden
(404) unless a token is configured, and require it via X-Debug-Token.
"""

import secrets
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from zikos.config import settings

router = APIRouter()


def _require_debug_access(x_debug_token: str | None) -> None:
    """Gate debug endpoints behind DEBUG_API_TOKEN.

    - Token not configured: endpoints do not exist (404).
    - Token configured: header must match (constant-time compare), else 403.
    """
    if not settings.debug_api_token:
        raise HTTPException(status_code=404, detail="Not Found")
    if not x_debug_token or not secrets.compare_digest(
        x_debug_token, settings.debug_api_token
    ):
        raise HTTPException(status_code=403, detail="Invalid or missing X-Debug-Token header")


def _check_history_integrity(history: list[dict]) -> list[dict]:
    """Return list of tool_use/tool_result pairing violations."""
    violations = []
    pending: dict[str, int] = {}  # tool_call_id → message index

    for i, msg in enumerate(history):
        tool_calls = msg.get("tool_calls") or []
        for tc in tool_calls:
            if isinstance(tc, dict) and tc.get("id"):
                pending[tc["id"]] = i

        tool_call_id = msg.get("tool_call_id")
        if tool_call_id:
            if tool_call_id in pending:
                del pending[tool_call_id]
            else:
                violations.append(
                    {
                        "type": "orphan_tool_result",
                        "tool_call_id": tool_call_id,
                        "message_index": i,
                        "tool_name": msg.get("name"),
                    }
                )

    for tc_id, msg_idx in pending.items():
        violations.append(
            {
                "type": "dangling_tool_use",
                "tool_call_id": tc_id,
                "message_index": msg_idx,
            }
        )

    return violations


def _summarise_history(history: list[dict]) -> list[dict]:
    summary = []
    for i, msg in enumerate(history):
        role = msg.get("role", "?")
        content_preview = str(msg.get("content") or "").replace("\n", " ")[:200]
        entry: dict = {"index": i, "role": role, "content_preview": content_preview}

        tool_calls = msg.get("tool_calls") or []
        if tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.get("id"),
                    "name": (tc.get("function") or {}).get("name"),
                }
                for tc in tool_calls
                if isinstance(tc, dict)
            ]

        tool_call_id = msg.get("tool_call_id")
        if tool_call_id:
            entry["tool_call_id"] = tool_call_id
            entry["tool_name"] = msg.get("name")

        summary.append(entry)
    return summary


@router.get("/session/{session_id}")
async def get_session_debug(
    session_id: str,
    x_debug_token: Annotated[str | None, Header()] = None,
):
    """Dump history and integrity check for a session. Requires DEBUG_API_TOKEN."""
    _require_debug_access(x_debug_token)

    from zikos.api.chat import get_chat_service

    llm_service = get_chat_service().llm_service
    history = llm_service.conversation_manager.conversations.get(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    violations = _check_history_integrity(history)
    return {
        "session_id": session_id,
        "message_count": len(history),
        "integrity_ok": len(violations) == 0,
        "violations": violations,
        "messages": _summarise_history(history),
    }


@router.get("/sessions")
async def list_sessions(x_debug_token: Annotated[str | None, Header()] = None):
    """List all active session IDs. Requires DEBUG_API_TOKEN."""
    _require_debug_access(x_debug_token)

    from zikos.api.chat import get_chat_service

    llm_service = get_chat_service().llm_service
    sessions = list(llm_service.conversation_manager.conversations.keys())
    return {"sessions": sessions}
