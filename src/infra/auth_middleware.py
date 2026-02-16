"""
Agent Optimus — Auth Middleware (Phase 15).
FastAPI middleware + dependencies for JWT/API key authentication.
"""

import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.auth_service import auth_service, AuthService

logger = logging.getLogger(__name__)

# FastAPI bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

# Routes that do NOT require authentication
PUBLIC_ROUTES = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
}


@dataclass
class CurrentUser:
    """Represents the authenticated user extracted from JWT or API key."""
    id: str
    email: str
    role: str  # admin | user | viewer
    auth_method: str = "jwt"  # jwt | api_key


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency: extracts and validates the user from the request.

    Supports two authentication methods:
    1. Bearer JWT token: Authorization: Bearer <token>
    2. API key header: X-API-Key: optimus_<key>
    """
    # Check if route is public
    if request.url.path in PUBLIC_ROUTES:
        return CurrentUser(id="anonymous", email="", role="viewer", auth_method="none")

    # Method 1: API Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        user_data = await auth_service.validate_api_key(api_key)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key inválida ou conta desativada.",
            )
        return CurrentUser(
            id=user_data["id"],
            email=user_data["email"],
            role=user_data["role"],
            auth_method="api_key",
        )

    # Method 2: Bearer JWT
    if credentials:
        payload = auth_service.decode_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido. Use um access token.",
            )
        return CurrentUser(
            id=payload["sub"],
            email=payload.get("email", ""),
            role=payload.get("role", "user"),
            auth_method="jwt",
        )

    # No auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticação necessária. Envie um Bearer token ou X-API-Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: str):
    """
    FastAPI dependency factory: ensures the user has at least the required role.

    Usage:
        @app.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def _check_role(user: CurrentUser = Depends(get_current_user)):
        if not AuthService.has_role(user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão insuficiente. Requer role '{required_role}', você é '{user.role}'.",
            )
        return user
    return _check_role


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser | None:
    """
    Like get_current_user, but returns None instead of raising 401.
    Useful for routes that work for both authenticated and anonymous users.
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
