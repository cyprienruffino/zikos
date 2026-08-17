"""Shared request validation helpers for API endpoints."""

import uuid

from fastapi import HTTPException


def validate_uuid(file_id: str, label: str = "file ID") -> str:
    """Validate that a path-supplied ID is a UUID before it touches the filesystem.

    Raises HTTP 400 for anything that is not a canonical UUID.
    """
    try:
        parsed = uuid.UUID(file_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {label}: must be a UUID") from None
    # Reject non-canonical forms (e.g. embedded braces/urn prefixes) so the
    # value used for pathing is exactly what was validated.
    if str(parsed) != file_id.lower():
        raise HTTPException(status_code=400, detail=f"Invalid {label}: must be a canonical UUID")
    return file_id
