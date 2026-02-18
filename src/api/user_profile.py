"""
Agent Optimus — User Profile & Preferences API (FASE 1).
Endpoints for user onboarding, name, and preferences management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from src.infra.auth_middleware import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["user"])


# ============================================
# Models
# ============================================


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str
    has_completed_onboarding: bool


class UpdateDisplayNameRequest(BaseModel):
    display_name: str


class UserPreferences(BaseModel):
    preferred_name: str = ""
    agent_name: str = "Optimus"
    language: str = "pt-BR"
    communication_style: str = "casual"
    timezone: str = "America/Sao_Paulo"


class CompleteOnboardingRequest(BaseModel):
    preferred_name: str
    agent_name: str = "Optimus"
    language: str = "pt-BR"
    communication_style: str = "casual"


# ============================================
# Endpoints
# ============================================


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(user: CurrentUser = Depends(get_current_user)) -> UserProfileResponse:
    """Get the authenticated user's profile."""
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT id, email, display_name, has_completed_onboarding FROM users WHERE id = :id"),
            {"id": user.id},
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        id=str(row[0]),
        email=row[1],
        display_name=row[2] or "",
        has_completed_onboarding=bool(row[3]),
    )


@router.put("/profile")
async def update_profile(
    request: UpdateDisplayNameRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Update the user's display name."""
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        await session.execute(
            text("UPDATE users SET display_name = :name, updated_at = now() WHERE id = :id"),
            {"name": request.display_name, "id": user.id},
        )
        await session.commit()

    logger.info(f"User {user.id} updated display_name to '{request.display_name}'")
    return {"success": True, "display_name": request.display_name}


@router.get("/preferences", response_model=UserPreferences)
async def get_preferences(user: CurrentUser = Depends(get_current_user)) -> UserPreferences:
    """Get the authenticated user's preferences."""
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        result = await session.execute(
            text("""
                SELECT preferred_name, agent_name, language, communication_style, timezone
                FROM user_preferences WHERE user_id = :user_id
            """),
            {"user_id": user.id},
        )
        row = result.fetchone()

    if not row:
        # Return defaults if no preferences set yet
        return UserPreferences()

    return UserPreferences(
        preferred_name=row[0] or "",
        agent_name=row[1] or "Optimus",
        language=row[2] or "pt-BR",
        communication_style=row[3] or "casual",
        timezone=row[4] or "America/Sao_Paulo",
    )


@router.put("/preferences", response_model=UserPreferences)
async def update_preferences(
    request: UserPreferences,
    user: CurrentUser = Depends(get_current_user),
) -> UserPreferences:
    """Update the user's preferences (upsert)."""
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        await session.execute(
            text("""
                INSERT INTO user_preferences (user_id, preferred_name, agent_name, language, communication_style, timezone)
                VALUES (:user_id, :preferred_name, :agent_name, :language, :communication_style, :timezone)
                ON CONFLICT (user_id) DO UPDATE SET
                    preferred_name = EXCLUDED.preferred_name,
                    agent_name = EXCLUDED.agent_name,
                    language = EXCLUDED.language,
                    communication_style = EXCLUDED.communication_style,
                    timezone = EXCLUDED.timezone,
                    updated_at = now()
            """),
            {
                "user_id": user.id,
                "preferred_name": request.preferred_name,
                "agent_name": request.agent_name,
                "language": request.language,
                "communication_style": request.communication_style,
                "timezone": request.timezone,
            },
        )
        await session.commit()

    logger.info(f"User {user.id} updated preferences: name='{request.preferred_name}', lang='{request.language}'")
    return request


@router.post("/onboarding/complete")
async def complete_onboarding(
    request: CompleteOnboardingRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Mark onboarding as complete. Saves preferred_name + preferences in one call.
    Called by onboarding.html on the last step.
    """
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        # Update display_name in users table
        await session.execute(
            text("UPDATE users SET display_name = :name, has_completed_onboarding = TRUE, updated_at = now() WHERE id = :id"),
            {"name": request.preferred_name, "id": user.id},
        )

        # Upsert preferences
        await session.execute(
            text("""
                INSERT INTO user_preferences (user_id, preferred_name, agent_name, language, communication_style)
                VALUES (:user_id, :preferred_name, :agent_name, :language, :communication_style)
                ON CONFLICT (user_id) DO UPDATE SET
                    preferred_name = EXCLUDED.preferred_name,
                    agent_name = EXCLUDED.agent_name,
                    language = EXCLUDED.language,
                    communication_style = EXCLUDED.communication_style,
                    updated_at = now()
            """),
            {
                "user_id": user.id,
                "preferred_name": request.preferred_name,
                "agent_name": request.agent_name,
                "language": request.language,
                "communication_style": request.communication_style,
            },
        )
        await session.commit()

    logger.info(f"User {user.id} completed onboarding as '{request.preferred_name}'")
    return {"success": True, "redirect": "/"}
