"""
Agent Optimus — FastAPI Application.
Auth + Chat + Files + Streaming.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import logging

from src.core.config import settings
from src.core.gateway import gateway
from src.core.files_service import files_service
from src.core.auth_service import auth_service
from src.infra.auth_middleware import (
    CurrentUser, get_current_user, get_optional_user, require_role,
)

logger = logging.getLogger(__name__)


def _schedule_daily_standup(cron_scheduler) -> None:
    """
    Schedule the daily standup at 12:00 UTC (09:00 BRT).
    Skips if a job named 'daily_standup' already exists (jobs persist across restarts).
    """
    from datetime import datetime, timedelta, timezone
    from src.core.cron_scheduler import CronJob

    existing = [j for j in cron_scheduler.list_jobs() if j.name == "daily_standup"]
    if existing:
        logger.info(f"FASE 0 #23: Daily standup already scheduled — next run: {existing[0].next_run}")
        return

    # Calculate next 12:00 UTC (today if not yet passed, otherwise tomorrow)
    now = datetime.now(timezone.utc)
    next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)

    job = CronJob(
        name="daily_standup",
        schedule_type="every",
        schedule_value="24h",
        payload="Generate team standup report",
        delete_after_run=False,
    )
    job_id = cron_scheduler.add(job)

    # Override next_run to 12:00 UTC (add() sets it to now+24h by default)
    cron_scheduler._jobs[job_id].next_run = next_run.isoformat()
    cron_scheduler._save()

    logger.info(f"FASE 0 #23: Daily standup scheduled — first run at {next_run.isoformat()}")


def _schedule_proactive_research(cron_scheduler) -> None:
    """
    Schedule proactive research every 8 hours (3x/day).
    Skips if a job named 'proactive_research' already exists (jobs persist across restarts).
    """
    from src.core.cron_scheduler import CronJob

    existing = [j for j in cron_scheduler.list_jobs() if j.name == "proactive_research"]
    if existing:
        logger.info(f"FASE 0 #6: Proactive research already scheduled — next run: {existing[0].next_run}")
        return

    job = CronJob(
        name="proactive_research",
        schedule_type="every",
        schedule_value="8h",
        payload="Run proactive research cycle",
        delete_after_run=False,
    )
    job_id = cron_scheduler.add(job)

    logger.info(f"FASE 0 #6: Proactive research scheduled — runs every 8h (3x/day), first run at {cron_scheduler._jobs[job_id].next_run}")


def _schedule_weekly_reflection(cron_scheduler) -> None:
    """
    Schedule weekly reflection analysis (every 168h / 7 days).
    Skips if a job named 'weekly_reflection' already exists (jobs persist across restarts).
    """
    from src.core.cron_scheduler import CronJob

    existing = [j for j in cron_scheduler.list_jobs() if j.name == "weekly_reflection"]
    if existing:
        logger.info(f"FASE 0 #7: Weekly reflection already scheduled — next run: {existing[0].next_run}")
        return

    job = CronJob(
        name="weekly_reflection",
        schedule_type="every",
        schedule_value="168h",  # 7 days
        payload="Analyze agent performance and generate reflection report",
        delete_after_run=False,
    )
    job_id = cron_scheduler.add(job)

    logger.info(f"FASE 0 #7: Weekly reflection scheduled — runs every 168h (7 days), first run at {cron_scheduler._jobs[job_id].next_run}")


def _schedule_pattern_learning(cron_scheduler) -> None:
    """
    Schedule weekly pattern learning (every 168h / 7 days).
    Skips if a job named 'pattern_learning' already exists (jobs persist across restarts).
    """
    from src.core.cron_scheduler import CronJob

    existing = [j for j in cron_scheduler.list_jobs() if j.name == "pattern_learning"]
    if existing:
        logger.info(f"FASE 0 #4: Pattern learning already scheduled — next run: {existing[0].next_run}")
        return

    job = CronJob(
        name="pattern_learning",
        schedule_type="every",
        schedule_value="168h",  # 7 days
        payload="Learn behavioral patterns from last 30 days",
        delete_after_run=False,
    )
    job_id = cron_scheduler.add(job)

    logger.info(f"FASE 0 #4: Pattern learning scheduled — runs every 168h (7 days), first run at {cron_scheduler._jobs[job_id].next_run}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    from src.infra.tracing import init_tracing
    from src.infra.migrate_all import run_migrations
    from src.core.cron_scheduler import cron_scheduler

    init_tracing()

    # Run DB migrations
    try:
        await run_migrations()
    except Exception as e:
        print(f"Migration failed: {e}")
        # We continue even if migration fails, to allow debugging
        pass

    await gateway.initialize()

    # FASE 0 #11: Load external MCP plugins from workspace/plugins/
    # Dynamic loading of custom tools via plugin system
    from pathlib import Path
    from src.skills.mcp_plugin import mcp_plugin_loader
    plugins_dir = Path(__file__).parent.parent / "workspace" / "plugins"
    if plugins_dir.exists():
        plugin_count = await mcp_plugin_loader.load_from_directory(str(plugins_dir))
        print(f"✅ FASE 0 #11: Loaded {plugin_count} MCP plugins from {plugins_dir}")
    else:
        print(f"ℹ️  FASE 0 #11: Plugins directory {plugins_dir} not found, skipping plugin loading")

    # FASE 0 #20: Register notification handlers on EventBus
    # TaskManager emits TASK_CREATED/UPDATED/COMPLETED → handlers send notifications
    from src.collaboration.notification_handlers import register_notification_handlers
    register_notification_handlers()

    # FASE 0 #22: Register activity feed handlers on EventBus
    # Records all task/message/cron events into ActivityFeed for /standup and audit
    from src.collaboration.activity_handlers import register_activity_handlers
    register_activity_handlers()

    # FASE 0 #23: Register standup cron handler on EventBus
    # CronScheduler fires CRON_TRIGGERED(job_name="daily_standup") → generates report
    from src.collaboration.standup_handlers import register_standup_handlers
    register_standup_handlers()

    # FASE 0 #6: Register proactive research cron handler on EventBus
    # CronScheduler fires CRON_TRIGGERED(job_name="proactive_research") → runs research cycle
    from src.engine.research_handlers import register_research_handlers
    register_research_handlers()

    # FASE 0 #7: Register weekly reflection cron handler on EventBus
    # CronScheduler fires CRON_TRIGGERED(job_name="weekly_reflection") → analyzes performance
    from src.engine.reflection_handlers import register_reflection_handlers
    register_reflection_handlers()

    # FASE 0 #4: Register pattern learning cron handler on EventBus
    # CronScheduler fires CRON_TRIGGERED(job_name="pattern_learning") → learns user patterns
    from src.engine.intent_handlers import register_intent_handlers
    register_intent_handlers()

    # FASE 0 #26: Start CronScheduler
    # Background loop checks for due jobs every 60s
    # Emits CRON_TRIGGERED events on EventBus
    await cron_scheduler.start()

    # FASE 0 #23: Schedule daily standup at 12:00 UTC (09:00 BRT)
    # Only adds the job if it doesn't already exist (jobs persist across restarts)
    _schedule_daily_standup(cron_scheduler)

    # FASE 0 #6: Schedule proactive research every 8h (3x/day)
    # Only adds the job if it doesn't already exist (jobs persist across restarts)
    _schedule_proactive_research(cron_scheduler)

    # FASE 0 #7: Schedule weekly reflection every 168h (7 days)
    # Only adds the job if it doesn't already exist (jobs persist across restarts)
    _schedule_weekly_reflection(cron_scheduler)

    # FASE 0 #4: Schedule weekly pattern learning every 168h (7 days)
    # Only adds the job if it doesn't already exist (jobs persist across restarts)
    _schedule_pattern_learning(cron_scheduler)

    # FASE 0 #16: Start WebChatChannel
    # Enables REST API + SSE streaming for web-based chat
    from src.channels.webchat import webchat_channel
    await webchat_channel.start()

    yield

    # Shutdown: stop cron scheduler and webchat channel
    await cron_scheduler.stop()
    await webchat_channel.stop()


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
# Static Files & UI
# ============================================
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static directory
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
async def root():
    """Serve the Chat UI."""
    return FileResponse("src/static/index.html")

@app.get("/login.html")
async def login_page():
    """Serve the Login page."""
    return FileResponse("src/static/login.html")

@app.get("/register.html")
async def register_page():
    """Serve the Register page."""
    return FileResponse("src/static/register.html")


# ============================================
# Health & Status (público)
# ============================================
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-optimus", "version": settings.VERSION}


@app.get("/api/v1/agents")
async def list_agents(user: CurrentUser = Depends(get_current_user)):
    """List all registered agents. Requires authentication."""
    agents = await gateway.get_agent_status()
    return {"status": "success", "data": agents}


# ============================================
# Auth Endpoints (públicos)
# ============================================
class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/v1/auth/register")
async def register(request: RegisterRequest):
    """Register a new user account."""
    try:
        result = await auth_service.register_user(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {e}")


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Authenticate and receive JWT tokens."""
    try:
        result = await auth_service.login(
            email=request.email,
            password=request.password,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {e}")


@app.post("/api/v1/auth/refresh")
async def refresh_token(request: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    try:
        result = await auth_service.refresh_access_token(request.refresh_token)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/v1/auth/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "status": "success",
        "data": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "auth_method": user.auth_method,
        },
    }


# ============================================
# Files (autenticado)
# ============================================
@app.post("/api/v1/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
):
    """Upload a file. user_id is extracted from the JWT automatically."""
    try:
        content = await file.read()
        result = await files_service.upload_file(
            file_content=content,
            filename=file.filename,
            user_id=user.id,
            conversation_id=conversation_id,
            mime_type=file.content_type,
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {e}")


# ============================================
# Chat (autenticado)
# ============================================
class ChatRequest(BaseModel):
    message: str
    agent: str | None = None
    context: dict | None = None
    file_ids: list[str] | None = None


@app.post("/api/v1/chat")
async def chat(request: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """Send a message to an agent. user_id is extracted from the JWT."""
    result = await gateway.route_message(
        message=request.message,
        user_id=user.id,
        target_agent=request.agent,
        context=request.context,
        file_ids=request.file_ids,
    )
    return {"status": "success", "data": result}


@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest, user: CurrentUser = Depends(get_current_user)):
    """Send a message and receive a streaming response (SSE)."""
    from sse_starlette.sse import EventSourceResponse
    import json

    async def event_generator():
        async for chunk in gateway.stream_route_message(
            message=request.message,
            user_id=user.id,
            target_agent=request.agent,
            context=request.context,
            file_ids=request.file_ids,
        ):
            yield {
                "event": chunk.get("type", "token"),
                "data": json.dumps(chunk),
            }
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())


@app.get("/api/v1/chat/history")
async def get_chat_history(
    agent: str = "optimus",
    limit: int = 30,
    user: CurrentUser = Depends(get_current_user),
):
    """Return the last N messages for the user's conversation with an agent."""
    from src.core.session_manager import session_manager

    conv = await session_manager.get_or_create_conversation(user.id, agent)
    messages = conv.get("messages", [])
    # Return last `limit` messages
    return {"status": "success", "data": messages[-limit:]}


# ============================================
# FASE 0 #16: WebChat Channel (SSE Streaming)
# ============================================
class WebChatSessionRequest(BaseModel):
    user_name: str = ""


class WebChatMessageRequest(BaseModel):
    session_id: str
    message: str
    context: dict | None = None


@app.post("/api/v1/webchat/session")
async def create_webchat_session(
    request: WebChatSessionRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new WebChat session. Returns session_id."""
    from src.channels.webchat import webchat_channel

    session_id = await webchat_channel.create_session(
        user_id=user.id,
        user_name=request.user_name or user.email,
    )
    return {"status": "success", "session_id": session_id}


@app.post("/api/v1/webchat/message")
async def send_webchat_message(
    request: WebChatMessageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Send a message to a WebChat session (async processing)."""
    from src.channels.webchat import webchat_channel

    await webchat_channel.receive_message(
        session_id=request.session_id,
        message=request.message,
        context=request.context,
    )
    return {"status": "success", "message": "processing"}


@app.get("/api/v1/webchat/stream/{session_id}")
async def stream_webchat_responses(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Stream responses for a WebChat session via SSE."""
    from src.channels.webchat import webchat_channel
    from sse_starlette.sse import EventSourceResponse
    import json

    async def event_generator():
        async for chunk in webchat_channel.stream_responses(session_id):
            yield {
                "event": chunk.get("type", "token"),
                "data": json.dumps(chunk),
            }

    return EventSourceResponse(event_generator())


@app.delete("/api/v1/webchat/session/{session_id}")
async def close_webchat_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Close a WebChat session."""
    from src.channels.webchat import webchat_channel

    await webchat_channel.close_session(session_id)
    return {"status": "success"}


# ============================================
# FASE 0 #5: Autonomous Executor (Jarvis Mode)
# ============================================
@app.get("/api/v1/autonomous/config")
async def get_autonomous_config(user: CurrentUser = Depends(get_current_user)):
    """Get autonomous executor configuration."""
    from src.engine.autonomous_executor import autonomous_executor

    return {
        "status": "success",
        "data": autonomous_executor.config.to_dict(),
    }


class AutonomousConfigUpdate(BaseModel):
    auto_execute_threshold: float | None = None
    max_risk_level: str | None = None
    daily_budget: int | None = None
    enabled: bool | None = None


@app.patch("/api/v1/autonomous/config")
async def update_autonomous_config(
    request: AutonomousConfigUpdate,
    user: CurrentUser = Depends(get_current_user),
):
    """Update autonomous executor configuration."""
    from src.engine.autonomous_executor import autonomous_executor

    config = autonomous_executor.config

    if request.auto_execute_threshold is not None:
        config.auto_execute_threshold = max(0.0, min(1.0, request.auto_execute_threshold))
    if request.max_risk_level is not None:
        config.max_risk_level = request.max_risk_level
    if request.daily_budget is not None:
        config.daily_budget = max(1, request.daily_budget)
    if request.enabled is not None:
        config.enabled = request.enabled

    autonomous_executor.save_config()

    return {
        "status": "success",
        "data": config.to_dict(),
        "message": "Configuration updated",
    }


@app.get("/api/v1/autonomous/audit")
async def get_autonomous_audit(
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
):
    """Get autonomous execution audit trail."""
    from src.engine.autonomous_executor import autonomous_executor

    trail = autonomous_executor.get_audit_trail(limit=limit)
    return {
        "status": "success",
        "data": trail,
        "count": len(trail),
    }


@app.get("/api/v1/autonomous/stats")
async def get_autonomous_stats(user: CurrentUser = Depends(get_current_user)):
    """Get autonomous executor statistics."""
    from src.engine.autonomous_executor import autonomous_executor

    stats = autonomous_executor.get_stats()
    return {
        "status": "success",
        "data": stats,
    }


# ============================================
# Admin-only endpoints
# ============================================
@app.get("/api/v1/admin/users", dependencies=[Depends(require_role("admin"))])
async def admin_list_users():
    """List all users. Admin only."""
    from src.infra.supabase_client import get_async_session
    from sqlalchemy import text

    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT id, email, display_name, role, is_active, created_at FROM users ORDER BY created_at DESC")
        )
        rows = result.fetchall()

    users = [
        {
            "id": str(r[0]),
            "email": r[1],
            "display_name": r[2],
            "role": r[3],
            "is_active": r[4],
            "created_at": r[5].isoformat() if r[5] else None,
        }
        for r in rows
    ]
    return {"status": "success", "data": users}


# ============================================
# Knowledge Base (RAG)
# ============================================
@app.post("/api/v1/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...), 
    user: CurrentUser = Depends(get_current_user)
):
    """Upload a document to the Knowledge Base (RAG)."""
    from src.core.knowledge_base import knowledge_base
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Read raw bytes (supports PDF, DOCX, etc.)
        content_bytes = await file.read()
        
        # Add to KB
        file_id = await knowledge_base.add_document(
            filename=file.filename,
            content=content_bytes,
            mime_type=file.content_type,
            user_id=user.id
        )
        return {"status": "success", "file_id": file_id}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Audio (TTS + STT)
# ============================================
class TTSRequest(BaseModel):
    text: str
    voice: str = "pt-BR-FranciscaNeural"


@app.post("/api/v1/audio/tts")
async def text_to_speech(
    request: TTSRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Convert text to speech using Edge TTS. Returns MP3 audio."""
    from src.core.audio_service import audio_service
    from fastapi.responses import Response

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        # Strip markdown symbols before speaking
        import re
        clean = re.sub(r"[*#_`~>]", "", request.text)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)  # links
        clean = clean.strip()[:2000]  # limit length

        audio_bytes = await audio_service.text_to_speech(clean, voice=request.voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/audio/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    """Transcribe audio using Groq Whisper. Returns the transcribed text."""
    from src.core.audio_service import audio_service, TranscriptionBackend

    try:
        content = await file.read()
        text = await audio_service.transcribe(
            content=content,
            mime_type=file.content_type or "audio/webm",
            backend=TranscriptionBackend.WHISPER,
        )
        return {"status": "success", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Debug Router (Manual DB Fix)
# ============================================
from src.api.v1.routers import debug
app.include_router(debug.router, prefix="/api/v1/debug", tags=["Debug"])

# FASE 0 #10: Collective Intelligence Knowledge API
from src.api.knowledge import router as knowledge_router
app.include_router(knowledge_router)

# FASE 0 #12: Skills Discovery API
from src.api.skills import router as skills_router
app.include_router(skills_router)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.post("/api/v1/knowledge/search")
async def search_knowledge(
    request: SearchRequest,
    user: CurrentUser = Depends(get_current_user)
):
    """Search the Knowledge Base."""
    from src.core.knowledge_base import knowledge_base
    results = await knowledge_base.search(request.query, limit=request.limit)
    return {"status": "success", "data": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
