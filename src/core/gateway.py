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
        target_agent: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """
        Route a message to the appropriate agent.

        Args:
            message: User message
            target_agent: Specific agent name (optional, auto-routes if None)
            context: Additional context (history, task, etc.)
        """
        await self.initialize()

        # If specific agent requested, use it
        if target_agent:
            agent = AgentFactory.get(target_agent)
            if not agent:
                return {
                    "content": f"❌ Agent '{target_agent}' não encontrado. Agents disponíveis: {[a['name'] for a in AgentFactory.list_agents()]}",
                    "agent": "gateway",
                    "model": "none",
                }
            return await agent.process(message, context)

        # Auto-route via Optimus
        optimus = AgentFactory.get("optimus")
        if not optimus:
            return {"content": "❌ Optimus não inicializado.", "agent": "gateway", "model": "none"}

        # For now, Optimus handles everything (delegation via sub-tasks in Phase 3)
        return await optimus.process(message, context)

    async def get_agent_status(self) -> list[dict]:
        """Get status of all agents."""
        await self.initialize()
        return AgentFactory.list_agents()


# Singleton
gateway = Gateway()
