"""
Agent Optimus — Agent Factory.
Creates, registers, and manages agent instances with configuration from SOUL.md and DB.
"""

import logging
from pathlib import Path

from src.agents.base import AgentConfig, BaseAgent
from src.identity.soul_loader import SoulLoader
from src.infra.redis_client import AgentRateLimiter

logger = logging.getLogger(__name__)

# Default workspace path for SOUL.md files
WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace"


class AgentFactory:
    """
    Factory for creating and managing agents.
    Agents are created from SOUL.md files + DB config.
    """

    _registry: dict[str, BaseAgent] = {}
    _rate_limiter: AgentRateLimiter | None = None

    @classmethod
    def set_rate_limiter(cls, rate_limiter: AgentRateLimiter):
        """Set the shared rate limiter for all agents."""
        cls._rate_limiter = rate_limiter

    @classmethod
    def create(
        cls,
        name: str,
        role: str,
        level: str = "specialist",
        model: str = "gemini-2.5-flash",
        model_chain: str = "default",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        soul_path: str | None = None,
        soul_content: str | None = None,
        agent_class: type[BaseAgent] | None = None,
        tools: list | None = None,
    ) -> BaseAgent:
        """
        Create a new agent and register it.

        Args:
            name: Unique agent name (e.g., 'optimus', 'friday')
            role: Agent role description
            level: Permission level (intern/specialist/lead)
            model: Default model to use
            model_chain: Failover chain name
            soul_path: Path to SOUL.md file (relative to workspace/souls/)
            soul_content: SOUL.md content directly (overrides soul_path)
            agent_class: Custom BaseAgent subclass (optional)
            tools: List of MCP tools (optional)
        """
        # Load SOUL.md
        soul_md = soul_content or ""
        if soul_path and not soul_content:
            full_path = WORKSPACE_DIR / "souls" / soul_path
            soul_md = SoulLoader.load(str(full_path))
        elif not soul_content:
            # Try default path
            default_path = WORKSPACE_DIR / "souls" / f"{name}.md"
            if default_path.exists():
                soul_md = SoulLoader.load(str(default_path))

        config = AgentConfig(
            name=name,
            role=role,
            level=level,
            model=model,
            model_chain=model_chain,
            max_tokens=max_tokens,
            temperature=temperature,
            soul_md=soul_md,
            tools=tools or [],
        )

        # Use custom class or default BaseAgent
        klass = agent_class or BaseAgent
        agent = klass(config=config, rate_limiter=cls._rate_limiter)

        cls._registry[name] = agent

        logger.info(f"Agent '{name}' created and registered", extra={"props": {
            "agent": name, "role": role, "level": level, "class": klass.__name__,
        }})

        return agent

    @classmethod
    def get(cls, name: str) -> BaseAgent | None:
        """Get a registered agent by name."""
        return cls._registry.get(name)

    @classmethod
    def get_all(cls) -> dict[str, BaseAgent]:
        """Get all registered agents."""
        return dict(cls._registry)

    @classmethod
    def list_agents(cls) -> list[dict]:
        """List all agents with their info."""
        return [
            {
                "name": agent.name,
                "role": agent.role,
                "level": agent.level,
                "model": agent.config.model,
            }
            for agent in cls._registry.values()
        ]

    @classmethod
    def remove(cls, name: str) -> bool:
        """Remove an agent from the registry."""
        if name in cls._registry:
            del cls._registry[name]
            logger.info(f"Agent '{name}' removed from registry")
            return True
        return False

    @classmethod
    def clear(cls):
        """Clear all registered agents."""
        cls._registry.clear()
