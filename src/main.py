"""
Agent Optimus — FastAPI Application.
~50 lines: app + middleware + routers + health.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.gateway import gateway


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize agents
    await gateway.initialize()
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="Agent Optimus",
    description="AI Agent Platform — Multi-sector, event-driven, MCP-first",
    version=settings.VERSION,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Health & Status
# ============================================
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-optimus", "version": settings.VERSION}


@app.get("/api/v1/agents")
async def list_agents():
    """List all registered agents."""
    agents = await gateway.get_agent_status()
    return {"status": "success", "data": agents}


# ============================================
# Chat
# ============================================
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    agent: str | None = None
    context: dict | None = None


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Send a message to an agent."""
    result = await gateway.route_message(
        message=request.message,
        target_agent=request.agent,
        context=request.context,
    )
    return {"status": "success", "data": result}
