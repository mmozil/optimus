"""
Agent Optimus — FastAPI Application.
~50 lines: app + middleware + routers + health.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.gateway import gateway
from src.core.files_service import files_service


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
    user_id: str = "default_user"
    agent: str | None = None
    context: dict | None = None
    file_ids: list[str] | None = None  # Reference previously uploaded files


@app.post("/api/v1/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form("default_user"),
    conversation_id: str | None = Form(None)
):
    """Upload a file and get its metadata/URL."""
    try:
        content = await file.read()
        result = await files_service.upload_file(
            file_content=content,
            filename=file.filename,
            user_id=user_id,
            conversation_id=conversation_id,
            mime_type=file.content_type
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Send a message to an agent."""
    result = await gateway.route_message(
        message=request.message,
        user_id=request.user_id,
        target_agent=request.agent,
        context=request.context,
        file_ids=request.file_ids,
    )
    return {"status": "success", "data": result}


@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """Send a message to an agent and receive a streaming response."""
    from sse_starlette.sse import EventSourceResponse
    import json

    async def event_generator():
        async for chunk in gateway.stream_route_message(
            message=request.message,
            user_id=request.user_id,
            target_agent=request.agent,
            context=request.context,
            file_ids=request.file_ids,
        ):
            yield {
                "event": chunk.get("type", "token"),
                "data": json.dumps(chunk)
            }
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())
