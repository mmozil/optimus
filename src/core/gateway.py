"""
Agent Optimus — Gateway (Control Plane).
Routes messages to agents, manages sessions, handles orchestration.
"""

import asyncio
import base64
import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.optimus import OptimusAgent
from src.core.agent_factory import AgentFactory

logger = logging.getLogger(__name__)

# Minimum response length to be worth sharing as a learning
_MIN_LEARNING_LEN = 150
# Max chars to store as the learning snippet
_MAX_LEARNING_LEN = 500
# Max chars for the topic label (derived from user message)
_MAX_TOPIC_LEN = 80

# Short messages that are not worth auto-sharing
_SKIP_PREFIXES = ("/", "ok", "sim", "não", "nao", "obrigado", "thanks", "oi", "olá", "hello", "ok!")


def _should_auto_share(message: str, response: str) -> bool:
    """Decide if a response is substantive enough to auto-share as a learning."""
    msg_lower = message.strip().lower()
    if any(msg_lower.startswith(p) for p in _SKIP_PREFIXES):
        return False
    if len(response.strip()) < _MIN_LEARNING_LEN:
        return False
    return True


async def _auto_share_learning(agent_name: str, message: str, response: str) -> None:
    """
    Auto-share a learning to CollectiveIntelligence after a substantive response.

    Fire-and-forget: called via asyncio.create_task(), never blocks the main response.
    Topic  = first N chars of the user message (what was asked).
    Learning = first N chars of the agent response (what was answered).
    """
    if not _should_auto_share(message, response):
        return
    try:
        from src.memory.collective_intelligence import collective_intelligence
        topic = message.strip()[:_MAX_TOPIC_LEN]
        learning = response.strip()[:_MAX_LEARNING_LEN]
        await collective_intelligence.async_share(
            agent_name=agent_name,
            topic=topic,
            learning=learning,
        )
    except Exception as e:
        logger.debug(f"Auto-share learning skipped: {e}")


async def _enrich_attachment_with_inline_data(att: dict) -> dict:
    """
    For audio attachments, download bytes from the public URL and store
    as base64 in 'content_base64' so _build_multimodal_content can send
    audio inline to Gemini (data URI format).
    Text/CSV files are read as UTF-8 and stored in 'text_content'.
    Images and PDFs are passed by URL — Gemini fetches them natively.
    """
    mime = att.get("mime_type", "")
    url = att.get("public_url", "")
    if not url:
        return att

    if mime.startswith("audio/"):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                att = dict(att)
                att["content_base64"] = base64.b64encode(resp.content).decode()
        except Exception as e:
            logger.warning(f"Could not fetch audio bytes for multimodal: {e}")

    elif mime in ("text/plain", "text/csv"):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                att = dict(att)
                att["text_content"] = resp.text[:8000]  # cap at 8k chars
        except Exception as e:
            logger.warning(f"Could not fetch text content for multimodal: {e}")

    return att


class Gateway:
    """
    Central control plane for the Agent Optimus platform.
    Routes messages to the appropriate agent based on intent.
    """

    def __init__(self):
        self._initialized = False

    async def initialize(self):
        """Initialize the gateway with agents from factory."""
        if self._initialized:
            return

        from src.infra.redis_client import AgentRateLimiter, redis_client

        # Set up shared rate limiter
        rate_limiter = AgentRateLimiter(redis_client)
        AgentFactory.set_rate_limiter(rate_limiter)

        # Default agent — only Optimus starts by default.
        # Specialized agents (developer, researcher, analyst, writer, guardian)
        # are created on demand when the user adds them via the Agents page.
        AgentFactory.create(
            name="optimus",
            role="Lead Orchestrator",
            level="lead",
            model="gemini-2.5-pro",
            model_chain="complex",
            max_tokens=8192,
            temperature=0.7,
            agent_class=OptimusAgent,
        )

        self._initialized = True
        logger.info(f"Gateway initialized with {len(AgentFactory.get_all())} agents")

    async def route_message(
        self,
        message: str,
        user_id: str = "default_user",
        target_agent: str | None = None,
        context: dict | None = None,
        file_ids: list[str] | None = None,
    ) -> dict:
        """
        Route a message to the appropriate agent.

        Enriched with:
        - Session Bootstrap (SOUL + MEMORY)
        - Emotional Analysis (Tone Adaptation)
        - File Attachments (Multimodal)
        - Chat Commands (slash commands)
        """
        await self.initialize()

        from src.infra.tracing import trace_span, trace_event

        with trace_span("gateway.route_message", {
            "user_id": user_id,
            "target_agent": target_agent or "auto",
            "message_length": len(message),
        }) as span:

            # FASE 0 #17: Chat Commands Integration
            # Check for slash commands BEFORE routing to agents
            from src.channels.chat_commands import chat_commands
            from src.channels.base_channel import IncomingMessage, ChannelType

            if chat_commands.is_command(message):
                # Create IncomingMessage for command handler
                cmd_message = IncomingMessage(
                    channel=ChannelType.WEBCHAT,
                    text=message,
                    user_id=user_id,
                    user_name=(context or {}).get("user_name", user_id),
                    chat_id=user_id,
                )

                cmd_result = await chat_commands.execute(cmd_message)
                if cmd_result:
                    trace_event("chat_command_executed", {"command": message.split()[0]})
                    return {
                        "content": cmd_result.text,
                        "agent": "chat_commands",
                        "model": "none",
                        "is_command": True,
                    }

            agent_name = target_agent or "optimus"

            # FASE 0 #3: Classify message intent for routing and analytics
            from src.engine.intent_classifier import intent_classifier
            intent_result = intent_classifier.classify(message)

            # FASE 0 #22: Emit MESSAGE_RECEIVED for ActivityFeed
            from src.core.events import event_bus, EventType
            await event_bus.emit_simple(
                EventType.MESSAGE_RECEIVED.value,
                source="gateway",
                data={
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "message_preview": message[:200],
                },
            )

            # 1. Initialize/Refresh Session Context
            from src.memory.session_bootstrap import session_bootstrap
            await session_bootstrap.load_context(agent_name)

            # 2. Analyze Sentiment
            from src.engine.emotional_adapter import emotional_adapter
            sentiment = emotional_adapter.analyze(message)

            # 3. Enrich context
            if context is None:
                context = {}
            context["user_id"] = user_id
            context["sentiment"] = sentiment
            context["tone_instruction"] = sentiment.tone_instruction

            # FASE 21 #5: Working Memory — load WORKING.md scratchpad into context
            # react_loop._build_user_content() already uses context["working_memory"] if present
            try:
                from src.memory.working_memory import working_memory as wm_service
                _wm_content = await wm_service.load(agent_name)
                if _wm_content and _wm_content.strip():
                    context["working_memory"] = _wm_content
            except Exception as _wm_e:
                logger.debug(f"FASE 21: Working memory load skipped: {_wm_e}")

            # FASE 21 #7: Context Awareness — ambient time/day context for the agent
            # Gives the agent awareness of current time, day of week, business hours
            try:
                from src.core.context_awareness import ContextAwareness
                _ambient = ContextAwareness().build_context()
                context["time_context"] = (
                    f"[{_ambient.greeting}, {_ambient.local_time} — {_ambient.day_of_week}. "
                    f"{_ambient.day_suggestion}]"
                )
            except Exception as _ca_e:
                logger.debug(f"FASE 21: Context awareness skipped: {_ca_e}")

            # FASE 0 #3: Add intent classification to context
            context["intent_classification"] = intent_result

            # Log intent for analytics
            trace_event("intent_classified", {
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
                "suggested_agent": intent_result.suggested_agent,
                "thinking_level": intent_result.thinking_level,
            })

            # Log mood to daily notes
            if sentiment.mood != "neutral":
                await emotional_adapter.log_mood("user", sentiment)

            # 4. Resolve file_ids to attachments (FASE 9: enrich audio/text with inline data)
            from src.core.files_service import files_service
            attachments = []
            if file_ids:
                for fid in file_ids:
                    info = await files_service.get_file_info(fid)
                    if info:
                        info = await _enrich_attachment_with_inline_data(info)
                        attachments.append(info)
            if attachments:
                context["attachments"] = attachments

            # 5. Load Conversation History
            from src.core.session_manager import session_manager
            conv = await session_manager.get_or_create_conversation(user_id, agent_name)
            context["history"] = conv["messages"]
            context["conversation_id"] = conv["id"]

            # 5b. Pending Reminders — inject into context for delivery
            from src.collaboration.reminder_delivery import pending_reminders
            reminders = pending_reminders.get_and_clear()
            if reminders:
                context["pending_reminders"] = reminders
                logger.info(f"Gateway: injecting {len(reminders)} pending reminder(s) into context")

            # 5c. FASE 21: RAG context enrichment for research/analysis intents
            # Only enriches when intent suggests it's needed — avoids latency on every request
            if intent_result.intent in ("research", "analysis") and len(message) > 20:
                try:
                    from src.infra.supabase_client import get_async_session
                    from src.memory.rag import rag_pipeline
                    async with get_async_session() as _rag_db:
                        _rag_ctx = await rag_pipeline.augment_prompt(_rag_db, message)
                        if _rag_ctx:
                            context["rag_context"] = _rag_ctx
                            logger.info(
                                f"FASE 21: RAG context injected ({len(_rag_ctx)} chars)",
                                extra={"props": {"intent": intent_result.intent, "rag_chars": len(_rag_ctx)}},
                            )
                except Exception as _rag_e:
                    logger.debug(f"FASE 21: RAG enrichment skipped: {_rag_e}")

            # 6. Planning Engine: detect complex tasks and propose a plan
            from src.engine.planning_engine import planning_engine
            if not target_agent and await planning_engine.should_plan(message, context):
                plan = await planning_engine.create_plan(message, context)
                plan_text = planning_engine.format_plan_for_user(plan)

                await session_manager.add_message(conv["id"], "user", message)
                await session_manager.add_message(conv["id"], "assistant", plan_text)

                trace_event("planning_triggered", {"steps": len(plan.steps)})

                return {
                    "content": plan_text,
                    "agent": "planning_engine",
                    "model": "gemini-2.5-flash",
                    "plan": {
                        "task": plan.task,
                        "steps": len(plan.steps),
                        "status": plan.status,
                    },
                }

            # FASE 21: Smart intent-based routing — use specialist agent when confidence > 0.5
            # intent_classifier already runs above; use suggested_agent if available
            context["thinking_level"] = intent_result.thinking_level
            if not target_agent and intent_result.confidence > 0.5 and intent_result.suggested_agent != "optimus":
                _specialist = intent_result.suggested_agent
                if AgentFactory.get(_specialist):
                    agent_name = _specialist
                    logger.info(
                        f"FASE 21: Intent routing '{intent_result.intent}' "
                        f"({intent_result.confidence:.0%}) → agent '{agent_name}'",
                        extra={"props": {"intent": intent_result.intent, "routed_to": agent_name}},
                    )

            # 7. Process
            if target_agent:
                agent = AgentFactory.get(target_agent)
                # FASE 3: If not found in registry, try loading from user_agents DB
                if not agent:
                    agent = await self._load_user_agent_from_db(target_agent, user_id)
                if not agent:
                    return {
                        "content": f"❌ Agent '{target_agent}' não encontrado. Agents disponíveis: {[a['name'] for a in AgentFactory.list_agents()]}",
                        "agent": "gateway",
                        "model": "none",
                    }
                # FASE 0 #1: Use think() instead of process() to enable ToT for complex queries
                result = await agent.think(message, context)
            else:
                # Use agent_name (may have been overridden by smart routing above)
                _agent = AgentFactory.get(agent_name)
                if not _agent:
                    _agent = AgentFactory.get("optimus")
                if not _agent:
                    return {"content": "❌ Optimus não inicializado.", "agent": "gateway", "model": "none"}
                # FASE 0 #1: Use think() instead of process() to enable ToT for complex queries
                result = await _agent.think(message, context)

            # FASE 0 #2: Apply 🔴 uncertainty warning if calibrated confidence is low
            # Format: "\n\n---\n\n🔴 ..." so TTS can strip it (split on "\n---\n")
            _uncertainty = result.get("uncertainty")
            if _uncertainty and _uncertainty.get("calibrated_confidence", 1.0) < 0.4:
                result = dict(result)
                result["content"] += f"\n\n---\n\n🔴 {_uncertainty['recommendation']}"

            # 8. Save Interaction to History
            await session_manager.add_message(conv["id"], "user", message)
            await session_manager.add_message(conv["id"], "assistant", result["content"])

            # FASE 12: Audit Trail — persist react_steps (fire-and-forget)
            _react_steps = result.get("steps", [])
            _react_usage = result.get("usage", {})
            _audit_session = str(conv.get("id", "")) if isinstance(conv, dict) else ""
            if _audit_session and (_react_steps or _react_usage):
                from src.core.audit_service import audit_service
                asyncio.create_task(audit_service.save(
                    session_id=_audit_session,
                    agent=result.get("agent", agent_name),
                    steps=_react_steps,
                    usage=_react_usage,
                    model=result.get("model", ""),
                ))

            # 9. Auto-share learning to CollectiveIntelligence (fire-and-forget)
            asyncio.create_task(_auto_share_learning(
                agent_name=result.get("agent", target_agent or "optimus"),
                message=message,
                response=result["content"],
            ))

            # FASE 21: Intent Predictor — add suggestion chips if patterns exist for this user
            try:
                from src.engine.intent_predictor import PATTERNS_DIR, UserPattern, intent_predictor
                import json as _json_pred
                _patterns_file = PATTERNS_DIR / f"{target_agent or 'optimus'}.json"
                if _patterns_file.exists():
                    _raw_patterns = _json_pred.loads(_patterns_file.read_text(encoding="utf-8"))
                    _patterns = [UserPattern(**p) for p in _raw_patterns]
                    if _patterns:
                        _predictions = intent_predictor.predict_next(_patterns)
                        if _predictions:
                            result = dict(result)
                            result["suggestions"] = [
                                {"text": p.suggested_message, "confidence": p.confidence, "action": p.action}
                                for p in _predictions[:3]
                            ]
                            logger.debug(f"FASE 21: {len(_predictions)} suggestion chips added to response")
            except Exception as _e_pred:
                logger.debug(f"FASE 21: Intent predictor suggestions skipped: {_e_pred}")

            # FASE 12: Expose conversation_id so frontend can query audit trail
            if _audit_session:
                result = dict(result)
                result["conversation_id"] = _audit_session

            if span:
                span.set_attribute("response.agent", result.get("agent", ""))
                span.set_attribute("response.model", result.get("model", ""))

            return result

    async def _load_user_agent_from_db(self, agent_slug: str, user_id: str) -> "BaseAgent | None":
        """
        FASE 3: Dynamically load a user-created agent from the DB.
        Creates and registers it in AgentFactory for subsequent requests.
        """
        try:
            from src.infra.supabase_client import get_async_session
            from sqlalchemy import text as sql_text

            async with get_async_session() as session:
                result = await session.execute(
                    sql_text("""
                        SELECT display_name, role, soul_md, model, temperature
                        FROM user_agents
                        WHERE agent_slug = :slug AND user_id = :uid AND is_active = TRUE
                    """),
                    {"slug": agent_slug, "uid": user_id},
                )
                row = result.fetchone()

            if not row:
                return None

            display_name, role, soul_md, model, temperature = row
            agent = AgentFactory.create(
                name=agent_slug,
                role=role or "Specialist",
                level="specialist",
                model=model or "gemini-2.5-flash",
                model_chain="default",
                temperature=float(temperature) if temperature else 0.7,
                soul_content=soul_md or "",
            )
            logger.info(f"FASE 3: Loaded user agent '{display_name}' (slug={agent_slug}) from DB")
            return agent

        except Exception as e:
            logger.warning(f"Failed to load user agent '{agent_slug}' from DB: {e}")
            return None

    async def stream_route_message(
        self,
        message: str,
        user_id: str = "default_user",
        target_agent: str | None = None,
        context: dict | None = None,
        file_ids: list[str] | None = None,
    ):
        """Streaming version of route_message."""
        await self.initialize()

        # FASE 0 #17: Chat Commands Integration (Streaming)
        from src.channels.chat_commands import chat_commands
        from src.channels.base_channel import IncomingMessage, ChannelType

        if chat_commands.is_command(message):
            cmd_message = IncomingMessage(
                channel=ChannelType.WEBCHAT,
                text=message,
                user_id=user_id,
                user_name=user_id,
                chat_id=user_id,
            )
            cmd_result = await chat_commands.execute(cmd_message)
            if cmd_result:
                # Return command result as single chunk
                yield {
                    "type": "token",
                    "content": cmd_result.text,
                    "agent": "chat_commands",
                    "model": "none",
                    "is_command": True,
                }
                return

        agent_name = target_agent or "optimus"

        # FASE 0 #3: Classify message intent
        from src.engine.intent_classifier import intent_classifier
        intent_result = intent_classifier.classify(message)

        # 1. Context loading (same as regular route)
        from src.memory.session_bootstrap import session_bootstrap
        await session_bootstrap.load_context(agent_name)

        from src.engine.emotional_adapter import emotional_adapter
        sentiment = emotional_adapter.analyze(message)

        if context is None:
            context = {}
        context["sentiment"] = sentiment
        context["tone_instruction"] = sentiment.tone_instruction
        context["intent_classification"] = intent_result  # FASE 0 #3

        # 2. Resolve file_ids to attachments (FASE 9: enrich audio/text with inline data)
        from src.core.files_service import files_service
        attachments = []
        if file_ids:
            for fid in file_ids:
                info = await files_service.get_file_info(fid)
                if info:
                    info = await _enrich_attachment_with_inline_data(info)
                    attachments.append(info)
        if attachments:
            context["attachments"] = attachments

        # 3. Load History
        from src.core.session_manager import session_manager
        conv = await session_manager.get_or_create_conversation(user_id, agent_name)
        context["history"] = conv["messages"]
        context["conversation_id"] = conv["id"]

        # 4. Routing
        agent = None
        if target_agent:
            agent = AgentFactory.get(target_agent)
            if not agent:
                yield {"type": "error", "content": f"Agent '{target_agent}' não encontrado."}
                return
        else:
            agent = AgentFactory.get("optimus")

        if not agent:
            yield {"type": "error", "content": "Optimus não inicializado."}
            return

        # 5. Stream and Capture result for history
        full_content = []
        async for chunk in agent.process(message, context, stream=True):
            if chunk.get("type") == "token":
                full_content.append(chunk.get("content", ""))
            yield chunk

        # 6. Save to History
        full_response = "".join(full_content)
        await session_manager.add_message(conv["id"], "user", message)
        await session_manager.add_message(conv["id"], "assistant", full_response)

        # 7. Auto-share learning to CollectiveIntelligence (fire-and-forget)
        asyncio.create_task(_auto_share_learning(
            agent_name=target_agent or "optimus",
            message=message,
            response=full_response,
        ))

    async def get_agent_status(self) -> list[dict]:
        """Get status of all agents."""
        await self.initialize()
        return AgentFactory.list_agents()


# Singleton
gateway = Gateway()
