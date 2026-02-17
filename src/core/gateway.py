"""
Agent Optimus — Gateway (Control Plane).
Routes messages to agents, manages sessions, handles orchestration.
"""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.optimus import OptimusAgent
from src.core.agent_factory import AgentFactory

logger = logging.getLogger(__name__)


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

        from src.agents.developer import FridayAgent
        from src.agents.researcher import FuryAgent
        from src.infra.redis_client import AgentRateLimiter, redis_client

        # Set up shared rate limiter
        rate_limiter = AgentRateLimiter(redis_client)
        AgentFactory.set_rate_limiter(rate_limiter)

        # Create initial squad
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

        AgentFactory.create(
            name="friday",
            role="Developer",
            level="specialist",
            model="gemini-2.5-flash",
            model_chain="default",
            max_tokens=4096,
            temperature=0.3,
            agent_class=FridayAgent,
        )

        AgentFactory.create(
            name="fury",
            role="Researcher",
            level="specialist",
            model="gemini-2.5-flash",
            model_chain="default",
            max_tokens=4096,
            temperature=0.5,
            agent_class=FuryAgent,
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
        """
        await self.initialize()

        from src.infra.tracing import trace_span, trace_event

        with trace_span("gateway.route_message", {
            "user_id": user_id,
            "target_agent": target_agent or "auto",
            "message_length": len(message),
        }) as span:

            # 1. Initialize/Refresh Session Context
            from src.memory.session_bootstrap import session_bootstrap
            await session_bootstrap.load_context()

            # 2. Analyze Sentiment
            from src.engine.emotional_adapter import emotional_adapter
            sentiment = emotional_adapter.analyze(message)

            # 3. Enrich context
            if context is None:
                context = {}
            context["user_id"] = user_id
            context["sentiment"] = sentiment
            context["tone_instruction"] = sentiment.tone_instruction

            # Log mood to daily notes
            if sentiment.mood != "neutral":
                await emotional_adapter.log_mood("user", sentiment)

            # 4. Resolve file_ids to attachments
            from src.core.files_service import files_service
            attachments = []
            if file_ids:
                for fid in file_ids:
                    info = await files_service.get_file_info(fid)
                    if info:
                        attachments.append(info)
            if attachments:
                context["attachments"] = attachments

            # 5. Load Conversation History
            from src.core.session_manager import session_manager
            agent_name = target_agent or "optimus"
            conv = await session_manager.get_or_create_conversation(user_id, agent_name)
            context["history"] = conv["messages"]
            context["conversation_id"] = conv["id"]

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

            # 7. Process
            if target_agent:
                agent = AgentFactory.get(target_agent)
                if not agent:
                    return {
                        "content": f"❌ Agent '{target_agent}' não encontrado. Agents disponíveis: {[a['name'] for a in AgentFactory.list_agents()]}",
                        "agent": "gateway",
                        "model": "none",
                    }
                result = await agent.process(message, context)
            else:
                optimus = AgentFactory.get("optimus")
                if not optimus:
                    return {"content": "❌ Optimus não inicializado.", "agent": "gateway", "model": "none"}
                result = await optimus.process(message, context)

            # 8. Save Interaction to History
            await session_manager.add_message(conv["id"], "user", message)
            await session_manager.add_message(conv["id"], "assistant", result["content"])

            if span:
                span.set_attribute("response.agent", result.get("agent", ""))
                span.set_attribute("response.model", result.get("model", ""))

            return result

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

        # 1. Context loading (same as regular route)
        from src.memory.session_bootstrap import session_bootstrap
        await session_bootstrap.load_context()

        from src.engine.emotional_adapter import emotional_adapter
        sentiment = emotional_adapter.analyze(message)
        
        if context is None:
            context = {}
        context["sentiment"] = sentiment
        context["tone_instruction"] = sentiment.tone_instruction

        # 2. Resolve file_ids to attachments
        from src.core.files_service import files_service
        attachments = []
        if file_ids:
            for fid in file_ids:
                info = await files_service.get_file_info(fid)
                if info:
                    attachments.append(info)
        if attachments:
            context["attachments"] = attachments

        # 3. Load History
        from src.core.session_manager import session_manager
        agent_name = target_agent or "optimus"
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
        await session_manager.add_message(conv["id"], "user", message)
        await session_manager.add_message(conv["id"], "assistant", "".join(full_content))

    async def get_agent_status(self) -> list[dict]:
        """Get status of all agents."""
        await self.initialize()
        return AgentFactory.list_agents()


# Singleton
gateway = Gateway()
