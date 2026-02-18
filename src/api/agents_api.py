"""
Agent Optimus — Dynamic Agents API (FASE 3).
CRUD for user-created custom agents.
"""

import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import text

from src.infra.auth_middleware import CurrentUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# System agents (hardcoded in gateway) — always available to all users
SYSTEM_AGENTS = [
    {"slug": "optimus", "display_name": "Optimus", "role": "Lead Orchestrator", "system": True},
    {"slug": "friday",  "display_name": "Friday",  "role": "Developer",          "system": True},
    {"slug": "fury",    "display_name": "Fury",    "role": "Researcher",          "system": True},
    {"slug": "analyst", "display_name": "Shuri",   "role": "Product Analyst",     "system": True},
    {"slug": "writer",  "display_name": "Loki",    "role": "Content Writer",      "system": True},
    {"slug": "guardian","display_name": "Vision",  "role": "QA / Security",       "system": True},
]

SOUL_TEMPLATE = """# SOUL.md — {name}

**Nome:** {name}
**Papel:** {role}
**Nível:** specialist
**Modelo:** gemini-2.5-flash

## Personalidade
Descreva a personalidade do agente aqui.
Seja específico sobre tom, estilo e abordagem.

## O Que Você Faz
- Liste as principais responsabilidades
- Seja específico sobre o domínio de atuação

## O Que Você NÃO Faz
- Liste o que está fora do escopo
- Delegue para outros agentes quando necessário

## Formato de Resposta
- Use markdown quando relevante
- Seja claro e objetivo
- Cite fontes quando possível
"""


def _make_slug(name: str) -> str:
    """Generate a URL-safe unique slug from agent name."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")[:30]
    suffix = uuid.uuid4().hex[:6]
    return f"{base}-{suffix}"


# ============================================
# Models
# ============================================

class AgentCreate(BaseModel):
    display_name: str
    role: str = "Specialist"
    soul_md: str = ""
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7

    @field_validator("display_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name cannot be empty")
        if len(v) > 100:
            raise ValueError("display_name max 100 chars")
        return v

    @field_validator("temperature")
    @classmethod
    def temp_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")
        return v


class AgentUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    soul_md: str | None = None
    model: str | None = None
    temperature: float | None = None


class AgentResponse(BaseModel):
    slug: str
    display_name: str
    role: str
    soul_md: str
    model: str
    temperature: float
    system: bool = False
    user_id: str | None = None


# ============================================
# Endpoints
# ============================================

@router.get("", response_model=list[AgentResponse])
async def list_agents(user: CurrentUser = Depends(get_current_user)) -> list[AgentResponse]:
    """List all agents: system agents + user's custom agents."""
    from src.infra.supabase_client import get_async_session

    # System agents first
    agents = [AgentResponse(**a, soul_md="", model="gemini-2.5-flash", temperature=0.7) for a in SYSTEM_AGENTS]

    # User's custom agents from DB
    try:
        async with get_async_session() as session:
            result = await session.execute(
                text("""
                    SELECT agent_slug, display_name, role, soul_md, model, temperature
                    FROM user_agents
                    WHERE user_id = :uid AND is_active = TRUE
                    ORDER BY created_at DESC
                """),
                {"uid": user.id},
            )
            rows = result.fetchall()

        for row in rows:
            agents.append(AgentResponse(
                slug=row[0],
                display_name=row[1],
                role=row[2],
                soul_md=row[3] or "",
                model=row[4] or "gemini-2.5-flash",
                temperature=float(row[5]) if row[5] is not None else 0.7,
                system=False,
                user_id=user.id,
            ))
    except Exception as e:
        logger.warning(f"Could not load user agents from DB: {e}")

    return agents


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    request: AgentCreate,
    user: CurrentUser = Depends(get_current_user),
) -> AgentResponse:
    """Create a new custom agent."""
    from src.infra.supabase_client import get_async_session

    slug = _make_slug(request.display_name)
    soul = request.soul_md or SOUL_TEMPLATE.format(
        name=request.display_name,
        role=request.role,
    )

    async with get_async_session() as session:
        await session.execute(
            text("""
                INSERT INTO user_agents (user_id, agent_slug, display_name, role, soul_md, model, temperature)
                VALUES (:uid, :slug, :name, :role, :soul, :model, :temp)
            """),
            {
                "uid": user.id,
                "slug": slug,
                "name": request.display_name,
                "role": request.role,
                "soul": soul,
                "model": request.model,
                "temp": request.temperature,
            },
        )
        await session.commit()

    logger.info(f"User {user.id} created agent '{request.display_name}' (slug={slug})")
    return AgentResponse(
        slug=slug,
        display_name=request.display_name,
        role=request.role,
        soul_md=soul,
        model=request.model,
        temperature=request.temperature,
        system=False,
        user_id=user.id,
    )


@router.get("/{agent_slug}", response_model=AgentResponse)
async def get_agent(
    agent_slug: str,
    user: CurrentUser = Depends(get_current_user),
) -> AgentResponse:
    """Get a specific agent (system or user's own)."""
    # Check system agents
    for sa in SYSTEM_AGENTS:
        if sa["slug"] == agent_slug:
            return AgentResponse(**sa, soul_md="", model="gemini-2.5-flash", temperature=0.7)

    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        result = await session.execute(
            text("""
                SELECT agent_slug, display_name, role, soul_md, model, temperature
                FROM user_agents
                WHERE agent_slug = :slug AND user_id = :uid AND is_active = TRUE
            """),
            {"slug": agent_slug, "uid": user.id},
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")

    return AgentResponse(
        slug=row[0], display_name=row[1], role=row[2],
        soul_md=row[3] or "", model=row[4] or "gemini-2.5-flash",
        temperature=float(row[5]) if row[5] is not None else 0.7,
        system=False, user_id=user.id,
    )


@router.put("/{agent_slug}", response_model=AgentResponse)
async def update_agent(
    agent_slug: str,
    request: AgentUpdate,
    user: CurrentUser = Depends(get_current_user),
) -> AgentResponse:
    """Update a custom agent (only owner can update)."""
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        # Fetch current
        result = await session.execute(
            text("SELECT display_name, role, soul_md, model, temperature FROM user_agents WHERE agent_slug = :slug AND user_id = :uid AND is_active = TRUE"),
            {"slug": agent_slug, "uid": user.id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")

        new_name = request.display_name or row[0]
        new_role = request.role or row[1]
        new_soul = request.soul_md if request.soul_md is not None else row[2]
        new_model = request.model or row[3]
        new_temp = request.temperature if request.temperature is not None else float(row[4])

        await session.execute(
            text("""
                UPDATE user_agents
                SET display_name=:name, role=:role, soul_md=:soul, model=:model, temperature=:temp, updated_at=now()
                WHERE agent_slug=:slug AND user_id=:uid
            """),
            {"name": new_name, "role": new_role, "soul": new_soul, "model": new_model, "temp": new_temp, "slug": agent_slug, "uid": user.id},
        )
        await session.commit()

    # Evict from AgentFactory registry so it reloads next request
    from src.core.agent_factory import AgentFactory
    AgentFactory.remove(agent_slug)

    logger.info(f"User {user.id} updated agent '{agent_slug}'")
    return AgentResponse(
        slug=agent_slug, display_name=new_name, role=new_role,
        soul_md=new_soul, model=new_model, temperature=new_temp,
        system=False, user_id=user.id,
    )


@router.delete("/{agent_slug}", status_code=204)
async def delete_agent(
    agent_slug: str,
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Delete a custom agent (soft-delete)."""
    from src.infra.supabase_client import get_async_session

    async with get_async_session() as session:
        result = await session.execute(
            text("UPDATE user_agents SET is_active=FALSE, updated_at=now() WHERE agent_slug=:slug AND user_id=:uid AND is_active=TRUE"),
            {"slug": agent_slug, "uid": user.id},
        )
        await session.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")

    # Remove from factory registry
    from src.core.agent_factory import AgentFactory
    AgentFactory.remove(agent_slug)

    logger.info(f"User {user.id} deleted agent '{agent_slug}'")
