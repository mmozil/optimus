"""
Agent Optimus — Google OAuth API (FASE 4).
Handles OAuth2 flow for Gmail, Calendar, Drive.

Endpoints:
  GET  /api/v1/oauth/google/connect  → redirect to Google consent (public)
  GET  /api/v1/oauth/google/callback → exchange code, save tokens (public)
  GET  /api/v1/oauth/google/status   → connection status (authenticated)
  DELETE /api/v1/oauth/google/revoke → revoke tokens (authenticated)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.infra.auth_middleware import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/oauth/google", tags=["oauth"])


class OAuthStatusResponse(BaseModel):
    connected: bool
    google_email: str
    scopes: list[str]


# ============================================
# Public: OAuth flow
# ============================================

@router.get("/connect")
async def google_connect(token: str = ""):
    """
    Redirect user to Google OAuth consent page.
    Receives JWT token as query param (since this is a redirect, no Bearer header).
    """
    from src.core.config import settings
    from src.core.auth_service import auth_service

    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth não configurado. Adicione GOOGLE_OAUTH_CLIENT_ID no Coolify.",
        )

    # Validate JWT to get user_id
    if not token:
        raise HTTPException(status_code=401, detail="Token JWT necessário. Use ?token=<seu_token>")

    payload = auth_service.decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    user_id = payload["sub"]

    from src.core.google_oauth_service import google_oauth_service
    auth_url = google_oauth_service.get_auth_url(user_id)

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(code: str = "", state: str = "", error: str = ""):
    """
    Handle Google OAuth callback.
    Exchanges code for tokens, saves to DB, redirects to /settings.html.
    """
    if error:
        logger.warning(f"Google OAuth error: {error}")
        return RedirectResponse(url="/settings.html?google_error=access_denied")

    if not code or not state:
        return RedirectResponse(url="/settings.html?google_error=missing_params")

    try:
        from src.core.google_oauth_service import google_oauth_service
        result = await google_oauth_service.exchange_code(code=code, user_id=state)
        email = result.get("google_email", "")
        logger.info(f"Google OAuth connected for user {state} ({email})")
        return RedirectResponse(url=f"/settings.html?google_connected=1&email={email}")
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(url=f"/settings.html?google_error={str(e)[:100]}")


# ============================================
# Authenticated: status + revoke
# ============================================

@router.get("/status", response_model=OAuthStatusResponse)
async def google_status(user: CurrentUser = Depends(get_current_user)) -> OAuthStatusResponse:
    """Get Google OAuth connection status for the current user."""
    from src.core.google_oauth_service import google_oauth_service
    status = await google_oauth_service.get_connection_status(user.id)
    return OAuthStatusResponse(**status)


@router.delete("/revoke", status_code=204)
async def google_revoke(user: CurrentUser = Depends(get_current_user)) -> None:
    """Revoke Google OAuth tokens for the current user."""
    from src.core.google_oauth_service import google_oauth_service
    await google_oauth_service.revoke(user.id)
    logger.info(f"Google OAuth revoked by user {user.id}")
