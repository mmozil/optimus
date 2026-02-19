"""
Agent Optimus — Apple iCloud API (FASE 8).
REST endpoints for managing Apple iCloud credentials and testing connection.

Call path:
  POST   /api/v1/apple/credentials  → apple_service.save_credentials(user_id, ...)
  GET    /api/v1/apple/status       → apple_service.get_credentials(user_id) → {connected, apple_id}
  DELETE /api/v1/apple/credentials  → apple_service.remove_credentials(user_id)
  GET    /api/v1/apple/test         → apple_service.test_connection(user_id) → live CalDAV check
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.infra.auth_middleware import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/apple", tags=["apple"])


class AppleCredentialsRequest(BaseModel):
    apple_id: str
    app_password: str
    display_name: str = ""


@router.post("/credentials", summary="Save Apple ID + App-Specific Password")
async def save_credentials(
    request: AppleCredentialsRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Save Apple iCloud credentials for the current user.
    app_password must be an App-Specific Password (NOT the Apple ID password).
    Generate at: https://appleid.apple.com → Security → App-Specific Passwords
    """
    from src.core.apple_service import apple_service

    result = await apple_service.save_credentials(
        user_id=str(user.id),
        apple_id=request.apple_id.strip(),
        app_password=request.app_password.strip(),
        display_name=request.display_name.strip(),
    )
    if not result.get("ok"):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao salvar"))
    return {"status": "success", "apple_id": result["apple_id"]}


@router.get("/status", summary="Check Apple iCloud connection status")
async def get_status(user: CurrentUser = Depends(get_current_user)):
    """Return whether the user has Apple iCloud configured (no live check)."""
    from src.core.apple_service import apple_service

    creds = await apple_service.get_credentials(str(user.id))
    if not creds:
        return {"connected": False}
    apple_id, _ = creds
    return {"connected": True, "apple_id": apple_id}


@router.get("/test", summary="Test Apple iCloud CalDAV connection (live)")
async def test_connection(user: CurrentUser = Depends(get_current_user)):
    """Attempt a live CalDAV connection and return calendars count."""
    from src.core.apple_service import apple_service

    result = await apple_service.test_connection(str(user.id))
    return result


@router.delete("/credentials", summary="Remove Apple iCloud credentials")
async def remove_credentials(user: CurrentUser = Depends(get_current_user)):
    """Delete stored Apple iCloud credentials for the current user."""
    from src.core.apple_service import apple_service

    result = await apple_service.remove_credentials(str(user.id))
    if not result.get("ok"):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result.get("error", "Erro ao remover"))
    return {"status": "success", "message": "Credenciais Apple removidas."}
